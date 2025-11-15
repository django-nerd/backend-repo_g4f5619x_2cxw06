import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel
from database import create_document

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Backend ready for Master Data Barang"}

# Schema for response
class ItemOut(BaseModel):
    id: str
    name: str
    category: str
    condition: str
    price: float
    description: Optional[str]
    image_url: Optional[str]

# Simple in-memory storage for uploaded files location (we'll store in /tmp and return url path)
UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/items", response_model=ItemOut)
async def create_item(
    name: str = Form(...),
    condition: str = Form(...),  # radio: e.g., "new" or "used"
    category: str = Form(...),   # select: e.g., "Elektronik", "Pakaian"
    price: float = Form(...),
    description: Optional[str] = Form(None),
    image: UploadFile = File(...),
):
    # Save uploaded file to UPLOAD_DIR
    filename = image.filename
    save_path = os.path.join(UPLOAD_DIR, filename)
    content = await image.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # For demo, serve as pseudo URL path (frontend will just display filename)
    image_url = f"/uploads/{filename}"

    # Persist to DB using schemas.Item layout indirectly via dict
    data = {
        "name": name,
        "category": category,
        "condition": condition,
        "price": float(price),
        "description": description,
        "image_url": image_url,
    }

    try:
        inserted_id = create_document("item", data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    return ItemOut(
        id=inserted_id,
        name=name,
        category=category,
        condition=condition,
        price=float(price),
        description=description,
        image_url=image_url,
    )

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
