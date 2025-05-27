import os
import httpx
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI, Request, Form, status, HTTPException
from fastapi.responses import RedirectResponse


load_dotenv()

ADSTERRA_API_KEY = os.getenv("ADSTERRA_API_KEY")
print("API KEY:", ADSTERRA_API_KEY)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Aktifkan middleware untuk session
app.add_middleware(SessionMiddleware, secret_key="RAHASIA_SUPER_AMAN")

# Dummy user database
USER_DB = {
    "tonxmedia": "Sukses2026"
}


def add_days(value, days):
    dt = datetime.strptime(value, "%Y-%m-%d").date()
    return (dt + timedelta(days=days)).isoformat()


templates.env.filters['add_days'] = add_days


def get_preset_dates(preset: str):
    utc_now = datetime.now(timezone.utc)
    today = utc_now.date()

    if preset == "today":
        return today, today
    elif preset == "yesterday":
        y = today - timedelta(days=1)
        return y, y
    elif preset == "last7":
        return today - timedelta(days=6), today
    elif preset == "last30":
        return today - timedelta(days=29), today
    elif preset == "thismonth":
        start = today.replace(day=1)
        return start, today
    elif preset == "thisyear":
        start = today.replace(month=1, day=1)
        return start, today
    else:
        return today, today


@app.get("/placements/{domain}")
async def get_placements(domain: int):
    url = f"https://api3.adsterratools.com/publisher/domain/{domain}/placements.json"
    headers = {
        "X-API-Key": ADSTERRA_API_KEY,
        "Accept": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                return JSONResponse(content={"items": items})
    except Exception as e:
        print("Error get placements:", e)

    return JSONResponse(content={"items": []})


@app.get("/domains")
async def get_domains():
    url = "https://api3.adsterratools.com/publisher/domains.json"
    headers = {
        "X-API-Key": ADSTERRA_API_KEY,
        "Accept": "application/json"
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                return JSONResponse(content={"items": items})
    except Exception as e:
        print("Error get domains:", e)
    return JSONResponse(content={"items": []})



# Cek apakah user sudah login


def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Belum login")
    return user

# Halaman login


@app.get("/login")
async def login_page(request: Request):
    # Kalau sudah login, langsung ke dashboard
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})

# Proses login


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    request.session.clear()
    if username in USER_DB and password == USER_DB[username]:
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Login gagal. Cek kembali data Anda."
    })

# Logout


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request,
                    start_date: str = Query(None),
                    end_date: str = Query(None),
                    preset: str = Query(None),
                    domain: str = Query(None),
                    placement: str = Query(None),
                    group_by: str = Query("date")):

    # Cek apakah user sudah login
    try:
        get_current_user(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=303)
    
    if preset:
        start, end = get_preset_dates(preset)
    else:
        utc_today = datetime.now(timezone.utc).date()
        start = datetime.strptime(
            start_date, "%Y-%m-%d").date() if start_date else utc_today
        end = datetime.strptime(
            end_date, "%Y-%m-%d").date() if end_date else utc_today

    start_str = start.isoformat()
    end_str = end.isoformat()

    base_url = "https://api3.adsterratools.com/publisher/stats.json"
    params = {
        "start_date": start_str,
        "finish_date": end_str,
        "group_by": group_by
    }

    if domain:
        params["domain"] = domain
    if placement:
        params["placement"] = placement

    headers = {
        "Accept": "application/json",
        "X-API-Key": ADSTERRA_API_KEY
    }

    stats_list = []
    summary = {
        "revenue": None,
        "impression": None,
        "clicks": None,
        "ctr": None,
        "cpm": None,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            stats_list = data.get("items", [])
            if stats_list:
                total_revenue = sum(float(item.get("revenue", 0) or 0)
                                    for item in stats_list)
                total_impression = sum(
                    int(item.get("impression", 0) or 0) for item in stats_list)
                total_clicks = sum(int(item.get("clicks", 0) or 0)
                                   for item in stats_list)
                total_ctr = (total_clicks / total_impression *
                             100) if total_impression > 0 else 0
                total_cpm = (total_revenue / total_impression *
                             1000) if total_impression > 0 else 0

                summary["revenue"] = f"{total_revenue:.3f}"
                summary["impression"] = total_impression
                summary["clicks"] = total_clicks
                summary["ctr"] = f"{total_ctr:.2f}"
                summary["cpm"] = f"{total_cpm:.3f}"
            else:
                summary["revenue"] = data.get("revenue")
                summary["impression"] = data.get("impression")
                summary["clicks"] = data.get("clicks")
                summary["ctr"] = data.get("ctr")
                summary["cpm"] = data.get("cpm")
        else:
            stats_list = []
    except Exception as e:
        print("Exception:", e)
        stats_list = []

    domain_list = [
        {"id": 1597430, "name": "1597430"},
    ]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats_list,
        "summary": summary,
        "start_date": start_str,
        "end_date": end_str,
        "preset": preset,
        "today": datetime.now(timezone.utc).date().isoformat(),
        "domain_list": domain_list,
        "selected_domain": domain,
        "selected_placement": placement,
        "group_by": group_by
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
