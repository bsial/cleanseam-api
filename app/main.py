"""
CleanSeam API - Quality scoring for conscious consumers
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os

app = FastAPI(
    title="CleanSeam API",
    description="Quality scoring and cost-per-wear analysis for clothing purchases",
    version="1.0.0",
)

# CORS for ChatGPT Actions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chat.openai.com", "https://chatgpt.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class AnalyzeRequest(BaseModel):
    brand: Optional[str] = None
    item_type: Optional[str] = None
    price: float
    currency: str = "USD"
    material_composition: Optional[str] = None
    url: Optional[str] = None


class AnalyzeResponse(BaseModel):
    quality_score: float = Field(..., ge=0, le=10)
    predicted_wears: int
    predicted_lifespan_months: int
    cost_per_wear: float
    verdict: str
    factors: dict
    brand_average: Optional[float] = None
    category_average: Optional[float] = None
    better_alternatives: list = []
    waitlist_url: str = "https://cleanseam.ai/join"


class BrandProfile(BaseModel):
    name: str
    overall_score: float
    tier: str
    description: str
    category_scores: dict
    avg_lifespan_months: int
    data_confidence: str


# --- Brand Database (MVP - hardcoded, replace with DB later) ---

BRAND_DATA = {
    "zara": {
        "name": "Zara",
        "tier": "fast_fashion",
        "overall_score": 3.5,
        "description": "Fast fashion with trendy designs, variable quality",
        "category_scores": {"jeans": 3.2, "t-shirt": 2.8, "dress": 3.5, "jacket": 4.0},
        "avg_lifespan_months": 12,
    },
    "h&m": {
        "name": "H&M",
        "tier": "fast_fashion",
        "overall_score": 3.0,
        "description": "Budget fast fashion, lower durability",
        "category_scores": {"jeans": 2.8, "t-shirt": 2.5, "dress": 3.0, "jacket": 3.5},
        "avg_lifespan_months": 10,
    },
    "uniqlo": {
        "name": "Uniqlo",
        "tier": "mid_range",
        "overall_score": 5.8,
        "description": "Quality basics, good value for price",
        "category_scores": {"jeans": 5.5, "t-shirt": 6.0, "jacket": 6.5, "pants": 5.8},
        "avg_lifespan_months": 24,
    },
    "patagonia": {
        "name": "Patagonia",
        "tier": "premium",
        "overall_score": 8.2,
        "description": "Durable outdoor wear, excellent longevity",
        "category_scores": {"jacket": 9.0, "t-shirt": 7.5, "pants": 8.0, "sweater": 8.5},
        "avg_lifespan_months": 60,
    },
    "shein": {
        "name": "Shein",
        "tier": "fast_fashion",
        "overall_score": 1.5,
        "description": "Ultra-fast fashion, minimal durability",
        "category_scores": {"jeans": 1.2, "t-shirt": 1.0, "dress": 1.8, "jacket": 2.0},
        "avg_lifespan_months": 6,
    },
    "levis": {
        "name": "Levi's",
        "tier": "mid_range",
        "overall_score": 6.5,
        "description": "Classic denim brand, good durability",
        "category_scores": {"jeans": 7.5, "jacket": 7.0, "t-shirt": 5.0, "shorts": 6.5},
        "avg_lifespan_months": 36,
    },
    "gap": {
        "name": "Gap",
        "tier": "mid_range",
        "overall_score": 4.5,
        "description": "Mid-range basics, inconsistent quality",
        "category_scores": {"jeans": 4.5, "t-shirt": 4.0, "sweater": 5.0, "jacket": 5.0},
        "avg_lifespan_months": 18,
    },
    "cos": {
        "name": "COS",
        "tier": "mid_range",
        "overall_score": 6.0,
        "description": "H&M premium line, better construction",
        "category_scores": {"dress": 6.5, "pants": 6.0, "jacket": 6.5, "t-shirt": 5.5},
        "avg_lifespan_months": 24,
    },
}

CATEGORY_AVERAGES = {
    "jeans": {"avg_score": 5.2, "avg_lifespan": 24, "avg_wears": 100},
    "t-shirt": {"avg_score": 4.5, "avg_lifespan": 18, "avg_wears": 60},
    "jacket": {"avg_score": 5.8, "avg_lifespan": 36, "avg_wears": 120},
    "dress": {"avg_score": 4.8, "avg_lifespan": 20, "avg_wears": 40},
    "pants": {"avg_score": 5.0, "avg_lifespan": 24, "avg_wears": 80},
    "sweater": {"avg_score": 5.5, "avg_lifespan": 30, "avg_wears": 70},
    "shirt": {"avg_score": 5.0, "avg_lifespan": 24, "avg_wears": 60},
    "shorts": {"avg_score": 4.5, "avg_lifespan": 24, "avg_wears": 50},
    "coat": {"avg_score": 6.0, "avg_lifespan": 48, "avg_wears": 150},
}


# --- Scoring Logic ---

def calculate_material_score(composition: Optional[str]) -> float:
    """Score material composition (higher natural fiber = better)"""
    if not composition:
        return 5.0  # neutral if unknown
    
    comp_lower = composition.lower()
    score = 5.0
    
    # Natural fibers boost
    if "100% cotton" in comp_lower or "100% wool" in comp_lower or "100% linen" in comp_lower:
        score += 3.0
    elif "cotton" in comp_lower:
        score += 1.5
    elif "wool" in comp_lower or "linen" in comp_lower:
        score += 2.0
    
    # Synthetic penalties
    if "polyester" in comp_lower:
        score -= 1.5
    if "acrylic" in comp_lower:
        score -= 2.0
    if "viscose" in comp_lower or "rayon" in comp_lower:
        score -= 0.5
    
    return max(1.0, min(10.0, score))


def get_brand_score(brand: str, category: str) -> tuple[float, dict]:
    """Get brand score for category, returns (score, brand_data)"""
    brand_key = brand.lower().strip()
    brand_data = BRAND_DATA.get(brand_key)
    
    if not brand_data:
        # Unknown brand - return neutral score
        return 5.0, None
    
    category_score = brand_data["category_scores"].get(category, brand_data["overall_score"])
    return category_score, brand_data


def calculate_predicted_wears(quality_score: float, category: str) -> int:
    """Estimate wears based on quality and category baseline"""
    category_data = CATEGORY_AVERAGES.get(category, {"avg_wears": 60})
    base_wears = category_data["avg_wears"]
    
    # Scale by quality score (5 = average)
    multiplier = quality_score / 5.0
    return int(base_wears * multiplier)


def calculate_lifespan(quality_score: float, category: str) -> int:
    """Estimate lifespan in months"""
    category_data = CATEGORY_AVERAGES.get(category, {"avg_lifespan": 18})
    base_lifespan = category_data["avg_lifespan"]
    
    multiplier = quality_score / 5.0
    return int(base_lifespan * multiplier)


def generate_verdict(quality_score: float, cost_per_wear: float, category_avg: float) -> str:
    """Generate human-readable verdict"""
    if quality_score >= 7.5:
        quality_desc = "Excellent quality"
    elif quality_score >= 5.5:
        quality_desc = "Good quality"
    elif quality_score >= 4.0:
        quality_desc = "Average quality"
    elif quality_score >= 2.5:
        quality_desc = "Below average quality"
    else:
        quality_desc = "Poor quality"
    
    if quality_score < category_avg - 1:
        comparison = "Below average for this category."
    elif quality_score > category_avg + 1:
        comparison = "Above average for this category."
    else:
        comparison = "Average for this category."
    
    if cost_per_wear < 1.0:
        value_note = "Good value per wear."
    elif cost_per_wear < 2.0:
        value_note = "Reasonable value."
    else:
        value_note = "Consider if you'll wear it enough to justify the cost."
    
    return f"{quality_desc}. {comparison} {value_note}"


def find_alternatives(brand: str, category: str, price: float, current_score: float) -> list:
    """Find better alternatives in similar price range"""
    alternatives = []
    
    for brand_key, brand_data in BRAND_DATA.items():
        if brand_key == brand.lower():
            continue
        
        cat_score = brand_data["category_scores"].get(category, brand_data["overall_score"])
        if cat_score > current_score + 0.5:  # meaningfully better
            alternatives.append({
                "brand": brand_data["name"],
                "score": cat_score,
                "typical_price_range": get_price_range(brand_data["tier"])
            })
    
    # Sort by score descending, limit to 3
    alternatives.sort(key=lambda x: x["score"], reverse=True)
    return alternatives[:3]


def get_price_range(tier: str) -> str:
    """Get typical price range for tier"""
    ranges = {
        "fast_fashion": "$10-50",
        "budget": "$15-40",
        "mid_range": "$40-100",
        "premium": "$80-250",
        "luxury": "$200+",
    }
    return ranges.get(tier, "$30-80")


# --- Endpoints ---

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_item(request: AnalyzeRequest):
    """Analyze a clothing item for quality and value"""
    
    if not request.brand and not request.url:
        raise HTTPException(status_code=400, detail="Brand or URL is required")
    
    if not request.item_type and not request.url:
        raise HTTPException(status_code=400, detail="Item type is required when not providing URL")
    
    # TODO: If URL provided, scrape product page for brand/item_type/composition
    
    brand = request.brand or "Unknown"
    item_type = (request.item_type or "t-shirt").lower()
    
    # Calculate scores
    brand_score, brand_data = get_brand_score(brand, item_type)
    material_score = calculate_material_score(request.material_composition)
    
    # Weighted quality score
    quality_score = (brand_score * 0.5) + (material_score * 0.3) + (brand_score * 0.2)  # construction proxy
    quality_score = round(min(10.0, max(1.0, quality_score)), 1)
    
    # Predictions
    predicted_wears = calculate_predicted_wears(quality_score, item_type)
    predicted_lifespan = calculate_lifespan(quality_score, item_type)
    cost_per_wear = round(request.price / predicted_wears, 2)
    
    # Category average
    category_data = CATEGORY_AVERAGES.get(item_type, {"avg_score": 5.0})
    category_avg = category_data["avg_score"]
    
    # Verdict
    verdict = generate_verdict(quality_score, cost_per_wear, category_avg)
    
    # Alternatives
    alternatives = find_alternatives(brand, item_type, request.price, quality_score)
    
    return AnalyzeResponse(
        quality_score=quality_score,
        predicted_wears=predicted_wears,
        predicted_lifespan_months=predicted_lifespan,
        cost_per_wear=cost_per_wear,
        verdict=verdict,
        factors={
            "brand_score": brand_score,
            "material_score": material_score,
        },
        brand_average=brand_data["overall_score"] if brand_data else None,
        category_average=category_avg,
        better_alternatives=alternatives,
    )


@app.get("/brand/{brand_name}", response_model=BrandProfile)
async def get_brand(brand_name: str):
    """Get quality profile for a brand"""
    brand_key = brand_name.lower().strip()
    brand_data = BRAND_DATA.get(brand_key)
    
    if not brand_data:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_name}' not found")
    
    return BrandProfile(
        name=brand_data["name"],
        overall_score=brand_data["overall_score"],
        tier=brand_data["tier"],
        description=brand_data["description"],
        category_scores=brand_data["category_scores"],
        avg_lifespan_months=brand_data["avg_lifespan_months"],
        data_confidence="medium",  # MVP has limited data
    )


@app.get("/compare")
async def compare_brands(brands: list[str], category: str):
    """Compare quality between brands for a category"""
    if len(brands) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 brands to compare")
    
    results = []
    for brand_name in brands:
        score, brand_data = get_brand_score(brand_name, category)
        predicted_wears = calculate_predicted_wears(score, category)
        
        results.append({
            "name": brand_data["name"] if brand_data else brand_name,
            "score": score,
            "typical_price": get_price_range(brand_data["tier"]) if brand_data else "Unknown",
            "predicted_wears": predicted_wears,
        })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Generate recommendation
    best = results[0]
    worst = results[-1]
    improvement = int(((best["predicted_wears"] / worst["predicted_wears"]) - 1) * 100)
    
    recommendation = f"{best['name']} offers best value with {improvement}% more predicted wears"
    
    return {
        "category": category,
        "brands": results,
        "recommendation": recommendation,
    }


@app.get("/categories")
async def list_categories():
    """List supported product categories"""
    return {
        "categories": [
            {"name": cat, "avg_score": data["avg_score"], "avg_lifespan_months": data["avg_lifespan"]}
            for cat, data in CATEGORY_AVERAGES.items()
        ]
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
