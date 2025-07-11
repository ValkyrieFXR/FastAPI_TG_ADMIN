from fastapi import FastAPI, Form, Query, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import json
import os
import shutil
import uuid
from datetime import datetime
from starlette.requests import Request as StarletteRequest

app = FastAPI()
templates = Jinja2Templates(directory="admin/templates")
app.mount("/static", StaticFiles(directory="admin/static"), name="static")

menu_path = "admin/menu_data.json"
upload_folder = "admin/static/uploads"
status_file = "admin/bot_status.json"
timers_log_path = "admin/timers_log.json"

if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

# ============================ Статус бота ============================

def read_bot_status():
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            status = json.load(f)
        return status.get("running", False)
    except:
        return False

@app.middleware("http")
async def add_bot_status_to_request(request: StarletteRequest, call_next):
    request.state.bot_running = read_bot_status()
    response = await call_next(request)
    return response

def render_with_globals(template_name: str, context: dict):
    request = context["request"]
    context["bot_running"] = getattr(request.state, "bot_running", False)
    return templates.TemplateResponse(template_name, context)

# ============================ Загрузка и сохранение меню ============================

def load_menu():
    if not os.path.exists(menu_path):
        return {}
    with open(menu_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_menu(data):
    with open(menu_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def flatten_buttons(buttons):
    flat = []
    for b in buttons:
        if isinstance(b, list):
            flat.extend(b)
        else:
            flat.append(b)
    return flat

def group_buttons(flat_buttons, groups):
    grouped = []
    i = 0
    while i < len(flat_buttons):
        if i < len(groups) and groups[i] == 2 and i + 1 < len(flat_buttons):
            grouped.append([flat_buttons[i], flat_buttons[i + 1]])
            i += 2
        else:
            grouped.append(flat_buttons[i])
            i += 1
    return grouped

# === TIMER LOG FUNCTIONALITY ===

def load_timers_log():
    if not os.path.exists(timers_log_path):
        return []
    with open(timers_log_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_timers_log(data):
    with open(timers_log_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================ Роуты ============================

@app.get("/", response_class=RedirectResponse)
async def root_redirect():
    return RedirectResponse("/overview")

@app.get("/overview", response_class=HTMLResponse)
async def overview(request: Request):
    return render_with_globals("overview.html", {
        "request": request,
        "active_page": "overview"
    })

@app.get("/statistics", response_class=HTMLResponse)
async def statistics(request: Request):
    return render_with_globals("statistics.html", {
        "request": request,
        "active_page": "statistics"
    })

@app.get("/logging", response_class=HTMLResponse)
async def logging_page(request: Request):
    return render_with_globals("logging.html", {
        "request": request,
        "active_page": "logging"
    })

@app.get("/planning", response_class=HTMLResponse)
async def planning(request: Request):
    return render_with_globals("planning.html", {
        "request": request,
        "active_page": "logging"
    })


@app.get("/edit_menu", response_class=HTMLResponse)
async def editor(request: Request, menu_key: str = "main"):
    menu = load_menu()
    if menu_key not in menu and menu:
        menu_key = list(menu.keys())[0]

    current_menu = menu.get(menu_key, {"text": "", "buttons": [], "photo": None, "button_groups": []})
    if "button_groups" not in current_menu or not current_menu["button_groups"]:
        current_menu["button_groups"] = [1] * len(current_menu.get("buttons", []))

    current_menu["buttons"] = flatten_buttons(current_menu.get("buttons", []))

    image_files = [
        f"/static/uploads/{f}" for f in os.listdir(upload_folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    ]

    return render_with_globals("edit_menu.html", {
        "request": request,
        "menu": menu,
        "menu_keys": list(menu.keys()),
        "current_key": menu_key,
        "current_menu": current_menu,
        "image_files": image_files,
        "active_page": "edit_menu"
    })

@app.post("/update", response_class=RedirectResponse)
async def update_menu(
    old_menu_key: str = Form(...),
    new_menu_key: str = Form(...),
    text: str = Form(...),
    button_texts: Optional[List[str]] = Form([]),
    button_callbacks: Optional[List[str]] = Form([]),
    button_links: Optional[List[str]] = Form([]),
    button_groups: Optional[List[int]] = Form([]),
    remove_photo: Optional[str] = Form(None),
    photo_file: Optional[UploadFile] = File(None),
    selected_photo: Optional[str] = Form(None)
):
    menu = load_menu()
    photo_path = menu.get(old_menu_key, {}).get("photo")

    # Удаление старого фото
    if remove_photo and photo_path:
        file_to_delete = os.path.join("admin", photo_path.lstrip("/"))
        if os.path.exists(file_to_delete):
            os.remove(file_to_delete)
        photo_path = None

    # Обработка нового изображения
    if photo_file and photo_file.filename:
        ext = os.path.splitext(photo_file.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(upload_folder, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(photo_file.file, buffer)
        photo_path = f"/static/uploads/{filename}"
    elif selected_photo:
        photo_path = selected_photo if selected_photo != "" else None

    # Сохранение кнопок и обновлений меню
    groups_int = []
    for g in button_groups:
        try:
            groups_int.append(int(g))
        except Exception:
            groups_int.append(1)
    while len(groups_int) < len(button_texts):
        groups_int.append(1)

    buttons = []
    i = 0
    n = len(button_texts)
    while i < n:
        t = button_texts[i].strip()
        c = button_callbacks[i].strip() if i < len(button_callbacks) else ""
        u = button_links[i].strip() if i < len(button_links) else ""
        g = groups_int[i] if i < len(groups_int) else 1
        if not t:
            i += 1
            continue

        btn = {"text": t}
        if u:
            btn["url"] = u
        elif c:
            btn["callback"] = c

        buttons.append(btn)
        i += 1

    grouped_buttons = group_buttons(buttons, groups_int)

    if old_menu_key != new_menu_key:
        if new_menu_key in menu:
            return RedirectResponse(f"/edit_menu?menu_key={old_menu_key}", status_code=303)
        menu.pop(old_menu_key, None)

    menu[new_menu_key] = {
        "text": text,
        "buttons": grouped_buttons,
        "button_groups": groups_int,
        "photo": photo_path
    }

    save_menu(menu)
    return RedirectResponse(f"/edit_menu?menu_key={new_menu_key}", status_code=303)



@app.post("/create_menu", response_class=RedirectResponse)
async def create_menu(menu_key: str = Form(...)):
    menu = load_menu()
    if menu_key and menu_key not in menu:
        menu[menu_key] = {
            "text": "Новое меню",
            "buttons": [],
            "photo": None,
            "button_groups": []
        }
        save_menu(menu)
    return RedirectResponse(f"/edit_menu?menu_key={menu_key}", status_code=303)

@app.post("/delete_menu", response_class=RedirectResponse)
async def delete_menu(menu_key: str = Form(...)):
    menu = load_menu()
    if menu_key in menu:
        photo_path = menu[menu_key].get("photo")
        if photo_path:
            file_path = os.path.join("admin", photo_path.lstrip("/"))
            if os.path.exists(file_path):
                os.remove(file_path)
        menu.pop(menu_key)
        save_menu(menu)
    return RedirectResponse(f"/edit_menu?menu_key={menu_key}", status_code=303)


@app.get("/edit_timers", response_class=HTMLResponse)
async def edit_timers(request: Request, menu_key: str = "main"):
    menu = load_menu()
    if menu_key not in menu:
        return RedirectResponse("/edit_menu")

    current_menu = menu[menu_key]
    buttons = flatten_buttons(current_menu.get("buttons", []))
    
    # Обработка статусов кнопок
    button_statuses = {}  # Состояние кнопок (активна/в ожидании)
    button_timers = {}  # Словарь для хранения состояния времени таймеров (пустое или с таймером)

    now = datetime.now()

    timers = current_menu.get("timers", {})
    button_delays = timers.get("button_delays", {})

    for btn in buttons:
        delay = button_delays.get(btn["text"])
        if delay:
            try:
                delay_time = datetime.fromisoformat(delay)
                if now < delay_time:
                    button_statuses[btn["text"]] = "В ожидании"
                    button_timers[btn["text"]] = delay  # Таймер не завершён
                else:
                    button_statuses[btn["text"]] = "Активна"
                    button_timers[btn["text"]] = None  # Таймер завершён, очищаем значение
            except Exception:
                button_statuses[btn["text"]] = "Активна"
                button_timers[btn["text"]] = None  # Таймер завершён, очищаем значение
        else:
            button_statuses[btn["text"]] = "Активна"
            button_timers[btn["text"]] = None  # Таймер завершён, очищаем значение
    
    return render_with_globals("edit_timers.html", {
        "request": request,
        "menu_keys": list(menu.keys()),
        "menu": current_menu,
        "buttons": buttons,
        "button_statuses": button_statuses,  # Статус кнопок
        "button_timers": button_timers,  # Состояние времени
        "current_key": menu_key,
        "active_page": "edit_menu"
    })


@app.post("/save_timers", response_class=RedirectResponse)
async def save_timers(
    request: Request,
    menu_key: str = Form(...),
    menu_start: str = Form(""),
    total_buttons: int = Form(...)
):
    form = await request.form()
    menu = load_menu()

    timers = {
        "menu_start": menu_start if menu_start else None,
        "button_delays": {}
    }

    # === Добавляем запись в лог новых таймеров ===
    timers_log = load_timers_log()
    now_str = datetime.now().isoformat(timespec="minutes")

    for i in range(1, int(total_buttons) + 1):
        text = form.get(f"button_text_{i}")
        time = form.get(f"button_timer_{i}")
        if text and time:
            timers["button_delays"][text] = time
            # Запись в лог (если нет такой записи)
            exists = any(
                entry["menu_key"] == menu_key and
                entry["button_text"] == text and
                entry["timer_time"] == time
                for entry in timers_log
            )
            if not exists:
                timers_log.append({
                    "id": str(uuid.uuid4()),
                    "menu_key": menu_key,
                    "button_text": text,
                    "timer_time": time,
                    "created_at": now_str
                })

    if menu_key in menu:
        menu[menu_key]["timers"] = timers
        save_menu(menu)

    save_timers_log(timers_log)  # Сохраняем лог

    return RedirectResponse(f"/edit_timers?menu_key={menu_key}", status_code=303)


@app.get("/publish_now", response_class=RedirectResponse)
async def publish_now(menu_key: str, button: str):
    menu = load_menu()
    if menu_key in menu:
        timers = menu[menu_key].get("timers", {})
        if "button_delays" in timers and button in timers["button_delays"]:
            # Удаляем таймер кнопки из button_delays
            timers["button_delays"].pop(button)
            timers["button_delays"][button] = None  # Устанавливаем статус кнопки на "Активна"
            save_menu(menu)

        # Удаляем из лога запись о завершённом таймере
        timers_log = load_timers_log()
        
        # Удаляем запись о завершённом таймере
        timers_log = [entry for entry in timers_log if not (entry["menu_key"] == menu_key and entry["button_text"] == button)]
        
        # Сохраняем обновленный лог
        save_timers_log(timers_log)

    return RedirectResponse(f"/edit_timers?menu_key={menu_key}", status_code=303)

# === Новый роут — страница логов таймеров ===
@app.get("/timers_log", response_class=HTMLResponse)
async def timers_log_page(request: Request):
    timers_log = load_timers_log()
    return render_with_globals("timers_log.html", {
        "request": request,
        "timers_log": timers_log,
        "active_page": "timers_log"
    })

# === Новый роут — удаление записи из лога ===
@app.post("/delete_timer", response_class=RedirectResponse)
async def delete_timer(timer_id: str = Form(...)):
    timers_log = load_timers_log()
    timers_log = [entry for entry in timers_log if entry["id"] != timer_id]
    save_timers_log(timers_log)
    return RedirectResponse("/timers_log", status_code=303)

# ============================ Запуск ============================

async def start_admin():
    import uvicorn
    config = uvicorn.Config("admin.admin_main:app", host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
