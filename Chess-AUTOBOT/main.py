import os, time, threading, tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import chess, chess.engine

# ── optional global hotkeys ─────────────────────────────────────
try:
    import keyboard  # pip install keyboard
    GLOBAL_KEYS = True
except ImportError:
    GLOBAL_KEYS = False
    print("`keyboard` not installed → global hotkeys disabled.")

# ── globals ─────────────────────────────────────────────────────
engine           = None
engine_running   = False
driver_browser   = None
current_board    = chess.Board()
last_game_url    = None
match_end_handled= False
CFG_PATH         = "stockfish_path.txt"

# ── GUI setup ───────────────────────────────────────────────────
root = tk.Tk()
root.title("Chess.com Live  •  Stockfish Helper")
root.attributes("-topmost", True)

# top‐row: Start/Stop/Refresh + status dot
top = tk.Frame(root); top.pack(fill=tk.X, padx=5, pady=5)
btn_start   = tk.Button(top, text="Start Stockfish  (1)")
btn_stop    = tk.Button(top, text="Stop  Stockfish  (2)")
btn_refresh = tk.Button(top, text="Refresh Moves  (3)")
btn_start.pack(side=tk.LEFT, padx=2)
btn_stop.pack(   side=tk.LEFT, padx=2)
btn_refresh.pack(side=tk.LEFT, padx=2)
dot = tk.Label(top, text="●", font=("Arial",14,"bold"), fg="red")
dot.pack(side=tk.LEFT, padx=8)
def update_dot():
    dot.config(fg="green" if engine_running else "red")

# engine options
opts = tk.Frame(root); opts.pack(fill=tk.X, padx=5)
path_var    = tk.StringVar()
time_var    = tk.DoubleVar(value=10.0)
depth_var   = tk.IntVar(value=20)
threads_var = tk.IntVar(value=4)
hash_var    = tk.IntVar(value=500)

def browse_sf():
    p = filedialog.askopenfilename(title="Select Stockfish executable")
    if p: path_var.set(p)

tk.Label(opts, text="Stockfish EXE:").grid(row=0, column=0, sticky="e")
tk.Entry(opts, textvariable=path_var, width=38)       .grid(row=0, column=1, columnspan=3, sticky="w")
tk.Button(opts, text="Browse…", command=browse_sf)    .grid(row=0, column=4, padx=4)
tk.Label(opts, text="Max Time (s)").grid( row=1, column=0, sticky="e")
tk.Spinbox(opts, from_=0.1, to=30.0, increment=0.1, textvariable=time_var, width=6)\
    .grid(row=1, column=1)
tk.Label(opts, text="Max Depth").grid(   row=1, column=2, sticky="e")
tk.Spinbox(opts, from_=1, to=100, textvariable=depth_var, width=5)\
    .grid(row=1, column=3)
tk.Label(opts, text="Threads").grid(     row=1, column=4, sticky="e")
tk.Spinbox(opts, from_=1, to=32, textvariable=threads_var, width=5)\
    .grid(row=1, column=5)
tk.Label(opts, text="Hash (MB)").grid(    row=1, column=6, sticky="e")
tk.Spinbox(opts, from_=16, to=4096, textvariable=hash_var, width=6)\
    .grid(row=1, column=7)

# status & move list
status_lbl = tk.Label(root, text="Waiting for a game…", fg="blue")
status_lbl.pack(pady=(6,0))
moves_box = ScrolledText(root, width=50, height=15, font=("Courier",12), state="disabled")
moves_box.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
def render_moves(sans):
    moves_box.config(state="normal"); moves_box.delete("1.0", tk.END)
    for i in range(0, len(sans), 2):
        n = i//2+1; w = sans[i]; b = sans[i+1] if i+1<len(sans) else ""
        moves_box.insert(tk.END, f"{n}. {w}" + (f" ...{b}" if b else "") + "\n")
    moves_box.config(state="disabled"); moves_box.see(tk.END)

# Stockfish output
tk.Label(root, text="Stockfish Output:").pack(pady=(10,0))
out_box = ScrolledText(root, width=50, height=5, font=("Courier",12), state="disabled")
out_box.pack(padx=5, pady=(0,10), fill=tk.BOTH)
def show_output(txt):
    out_box.config(state="normal"); out_box.delete("1.0", tk.END)
    out_box.insert(tk.END, txt); out_box.config(state="disabled"); out_box.see(tk.END)

# Match events
tk.Label(root, text="Match Events:").pack(pady=(10,0))
match_box = ScrolledText(root, width=50, height=3, font=("Courier",12), state="disabled")
match_box.pack(padx=5, pady=(0,10), fill=tk.BOTH)
def log_event(evt:str):
    match_box.config(state="normal")
    match_box.insert(tk.END, f"{time.strftime('%H:%M:%S')}  {evt}\n")
    match_box.config(state="disabled"); match_box.see(tk.END)

# load last path
if os.path.exists(CFG_PATH):
    try: path_var.set(open(CFG_PATH, encoding="utf-8").read().strip())
    except: pass

# ── Stockfish helpers ───────────────────────────────────────────
def configure_engine():
    if engine:
        try:
            engine.configure({
                "Threads": threads_var.get(),
                "Hash":    hash_var.get(),
                "Ponder":  "true"
            })
        except Exception as e:
            print("Engine config error:", e)

def clear_arrow():
    if driver_browser:
        driver_browser.execute_script(
          "const b=document.querySelector('wc-chess-board.board');"
          "if(!b) return;"
          "const g=b.querySelector('svg.arrows #stockfish-arrow');"
          "if(g) g.remove();"
        )

def _stop_engine(silent=False):
    global engine, engine_running
    if not engine_running: return
    engine_running=False
    if engine:
        try: engine.quit()
        except: pass
    engine=None
    update_dot(); clear_arrow(); show_output("")
    if not silent:
        messagebox.showinfo("Stockfish","Engine stopped.")

def draw_arrow(move:chess.Move):
    if not driver_browser: return
    src,dst = chess.square_name(move.from_square), chess.square_name(move.to_square)
    driver_browser.execute_script(f"""
    (function(){{
      const b=document.querySelector('wc-chess-board.board'); if(!b) return;
      let s=b.querySelector('svg.arrows');
      if(!s){{
        s=document.createElementNS('http://www.w3.org/2000/svg','svg');
        s.setAttribute('class','arrows'); s.setAttribute('viewBox','0 0 100 100');
        b.appendChild(s);
      }}
      const old=s.querySelector('#stockfish-arrow'); if(old) old.remove();
      const files='abcdefgh';
      function ctr(sq){{ let f=files.indexOf(sq[0]),r=parseInt(sq[1])-1;
         return [12.5*f+6.25,100-(12.5*r+6.25)]; }}
      const [x1,y1]=ctr('{src}'),[x2,y2]=ctr('{dst}');
      const NS='http://www.w3.org/2000/svg';
      const g=document.createElementNS(NS,'g'); g.setAttribute('id','stockfish-arrow');
      const m=document.createElementNS(NS,'marker');
      m.setAttribute('id','ah'); m.setAttribute('markerWidth','8');
      m.setAttribute('markerHeight','6'); m.setAttribute('refX','8');
      m.setAttribute('refY','3'); m.setAttribute('orient','auto');
      const p=document.createElementNS(NS,'path');
      p.setAttribute('d','M0,0 L8,3 L0,6 Z');
      p.setAttribute('fill','rgba(255,0,0,0.9)'); m.appendChild(p); g.appendChild(m);
      const l=document.createElementNS(NS,'line');
      l.setAttribute('x1',x1);l.setAttribute('y1',y1);
      l.setAttribute('x2',x2);l.setAttribute('y2',y2);
      l.setAttribute('stroke','rgba(255,0,0,0.9)'); l.setAttribute('stroke-width','2');
      l.setAttribute('stroke-linecap','round');
      l.setAttribute('marker-end','url(#ah)'); g.appendChild(l);
      s.appendChild(g);
    }})();""")

def analyse_and_display(board_copy):
    try:
        configure_engine()
        limit = chess.engine.Limit(time=time_var.get(), depth=depth_var.get())
        info = engine.analyse(board_copy, limit)
        best = info["pv"][0] if "pv" in info else info["bestmove"]
        sc = info["score"].white()
        ev = f"Mate {sc.mate()}" if sc.is_mate() else f"{sc.score()/100:.2f}"
        root.after(0, show_output, f"Best: {best}    Eval: {ev}")
        draw_arrow(best)
    except Exception as e:
        root.after(0, show_output, f"Analysis error: {e}")

def start_engine(evt=None):
    global engine, engine_running
    if engine_running: return
    exe = path_var.get().strip()
    if not exe or not os.path.isfile(exe):
        return messagebox.showerror("Select Engine","Pick a valid Stockfish binary.")
    engine = chess.engine.SimpleEngine.popen_uci(exe)
    configure_engine()
    engine_running=True; update_dot()
    open(CFG_PATH,"w").write(exe)
    messagebox.showinfo("Stockfish","Engine started.")
    # immediate analyse of current position
    threading.Thread(target=analyse_and_display,
                     args=(current_board.copy(),), daemon=True).start()

def stop_engine(evt=None):
    _stop_engine()

def refresh_moves(evt=None):
    global current_board, match_end_handled
    render_moves([]); clear_arrow()
    current_board = chess.Board()
    match_end_handled = False
    if engine_running and engine:
        try: engine.ucinewgame()
        except: pass
        threading.Thread(target=analyse_and_display,
                         args=(current_board.copy(),), daemon=True).start()
    log_event("Manual refresh")

btn_start   .config(command=start_engine)
btn_stop    .config(command=stop_engine)
btn_refresh .config(command=refresh_moves)
root.bind("1", start_engine)
root.bind("2", stop_engine)
root.bind("3", refresh_moves)
if GLOBAL_KEYS:
    keyboard.add_hotkey('1', lambda: root.after(0,start_engine))
    keyboard.add_hotkey('2', lambda: root.after(0,stop_engine))
    keyboard.add_hotkey('3', lambda: root.after(0,refresh_moves))

update_dot()

# ── browser & watcher thread ─────────────────────────────────────
def browser_and_watch():
    global driver_browser, current_board, last_game_url, match_end_handled
    drv = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),
                           options=Options().add_argument("--start-maximized"))
    driver_browser = drv
    drv.get("https://www.chess.com/live")

    # wait for first game URL
    while "/game/" not in drv.current_url:
        time.sleep(0.4)
    last_game_url = drv.current_url
    match_end_handled = False
    render_moves([])
    clear_arrow()
    log_event("New match started")
    root.after(0, lambda: status_lbl.config(text="Game in progress", fg="green"))

    # locate move-list
    while True:
        try:
            mlist = drv.find_element(By.CSS_SELECTOR, "wc-simple-move-list")
            break
        except:
            time.sleep(0.4)

    seen, board = [], chess.Board()
    current_board = board.copy()

    while True:
        try:
            # check for URL change → new match
            if drv.current_url != last_game_url and "/game/" in drv.current_url:
                last_game_url = drv.current_url
                match_end_handled = False
                board.reset(); current_board = board.copy(); seen.clear()
                root.after(0, render_moves, [])
                root.after(0, clear_arrow)
                log_event("New match started")
                root.after(0, lambda: status_lbl.config(text="Game in progress", fg="green"))
                if engine_running and engine:
                    try: engine.ucinewgame()
                    except: pass

            # check for result row → match end
            if not match_end_handled:
                res = drv.find_elements(By.CSS_SELECTOR,
                    "wc-simple-move-list .move-list-row.result-row span.game-result")
                if res and res[0].text.strip():
                    result = res[0].text.strip()
                    match_end_handled = True
                    log_event(f"Match ended: {result}")
                    _stop_engine(silent=True)
                    root.after(0, status_lbl.config, {"text":f"Match ended: {result}", "fg":"red"})
                    continue  # skip move parsing

            # parse moves only if match active
            if not match_end_handled:
                elems = mlist.find_elements(By.CSS_SELECTOR, "span.node-highlight-content")
                now = []
                for e in elems:
                    ico = e.find_elements(By.CSS_SELECTOR, "span.icon-font-chess")
                    p   = ico[0].get_attribute("data-figurine") if ico else ""
                    t   = e.text.strip()
                    now.append(f"{p}{t}" if p else t)

                if now != seen:
                    # push new moves
                    for san in now[len(seen):]:
                        try: board.push_san(san)
                        except: pass
                    current_board = board.copy()
                    root.after(0, render_moves, now)
                    seen[:] = now
                    if engine_running and engine:
                        threading.Thread(target=analyse_and_display,
                                         args=(board.copy(),), daemon=True).start()

        except Exception as e:
            print("Watcher error:", e)
            break

        time.sleep(0.6)

threading.Thread(target=browser_and_watch, daemon=True).start()

# ── cleanup ───────────────────────────────────────────────────────
def on_close():
    if GLOBAL_KEYS:
        keyboard.unhook_all()
    _stop_engine(silent=True)
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
