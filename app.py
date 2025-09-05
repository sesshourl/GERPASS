import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import pyperclip
import json
import os
import pyotp

APPDATA = os.getenv("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
GERPASS_DIR = os.path.join(APPDATA, "GERPASS")
os.makedirs(GERPASS_DIR, exist_ok=True)
ARQUIVO = os.path.join(GERPASS_DIR, "senhas.json.enc")

from cryptography.fernet import Fernet

KEY_FILE = os.path.join(GERPASS_DIR, "key.key")
if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
else:
    with open(KEY_FILE, "rb") as f:
        key = f.read()
fernet = Fernet(key)

root = tk.Tk()
root.title("Gerenciador de Senhas")
style = ttk.Style()
style.theme_use("alt")
root.geometry("800x600")

senhas = []

def ask_input(title, prompt, show=None):
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.transient(root)
    dialog.grab_set()
    tk.Label(dialog, text=prompt).pack(padx=10, pady=10)
    entry = tk.Entry(dialog, show=show) if show else tk.Entry(dialog)
    entry.pack(padx=10, pady=10)
    entry.focus_force()

    dialog.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = root.winfo_y() + (root.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")

    result = []

    def on_ok():
        result.append(entry.get())
        dialog.destroy()

    entry.bind("<Return>", lambda _: on_ok())
    tk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
    dialog.wait_window()
    return result[0] if result else None

def carregar_senhas():
    global senhas
    if os.path.exists(ARQUIVO):
        try:
            with open(ARQUIVO, "r", encoding="utf-8") as f:
                senhas = json.load(f)
        except (json.JSONDecodeError, IOError):
            senhas = []
    else:
        senhas = []

def salvar_senhas():
    try:
        data = json.dumps(senhas, ensure_ascii=False, indent=2).encode("utf-8")
        encrypted = fernet.encrypt(data)
        with open(ARQUIVO, "wb") as f:
            f.write(encrypted)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao salvar senhas: {e}", parent=root)

def listar_senhas():
    for item in tree.get_children():
        tree.delete(item)
    for idx, s in enumerate(senhas):
        try:
            otp = pyotp.TOTP(s['otp_secret']).now() if s.get('otp_secret') else ""
        except Exception:
            otp = ""
        tree.insert("", "end", iid=idx, values=(s['Servidor'], s['usuario'], s['senha'], otp))


def carregar_senhas():
    global senhas
    if os.path.exists(ARQUIVO):
        try:
            with open(ARQUIVO, "rb") as f:
                encrypted = f.read()
            data = fernet.decrypt(encrypted)
            senhas = json.loads(data.decode("utf-8"))
        except Exception:
            senhas = []
    else:
        senhas = []

def cadastrar_senha():
    servidor = ask_input("Servidor", "Nome do servidor:")
    usuario = ask_input("Usuário", "Nome do usuário:")
    senha = ask_input("Senha", "Digite a senha:", show="*")
    if servidor and usuario and senha:
        senhas.append({
            'Servidor': servidor,
            'usuario': usuario,
            'senha': '*' * len(senha),
            'senha_real': senha,
            'otp_secret': ""  # campo vazio por padrão
        })
        salvar_senhas()
        listar_senhas()
        messagebox.showinfo("Sucesso", "Senha cadastrada!", parent=root)

def configurar_otp():
    selected = tree.selection()
    if selected:
        idx = int(selected[0])
        otp_secret = ask_input("OTP Secret", "Cole aqui o segredo OTP fornecido pelo site:")
        if otp_secret:
            senhas[idx]['otp_secret'] = otp_secret
            salvar_senhas()
            listar_senhas()
            messagebox.showinfo("Sucesso", "OTP configurado!", parent=root)

def copiar_por_clique(event):
    item = tree.identify_row(event.y)
    col = tree.identify_column(event.x)
    if item and col:
        idx = int(item)
        if col == "#1":
            pyperclip.copy(senhas[idx]['Servidor'])
            messagebox.showinfo("Copiado", "Servidor copiado para área de transferência!")
        elif col == "#2":
            pyperclip.copy(senhas[idx]['usuario'])
            messagebox.showinfo("Copiado", "Login copiado para área de transferência!")
        elif col == "#3":
            pyperclip.copy(senhas[idx]['senha_real'])
            messagebox.showinfo("Copiado", "Senha copiada para área de transferência!")
        elif col == "#4":
            try:
                if senhas[idx].get('otp_secret'):
                    otp = pyotp.TOTP(senhas[idx]['otp_secret']).now()
                    pyperclip.copy(otp)
                    messagebox.showinfo("Copiado", "OTP copiado para área de transferência!")
                else:
                    messagebox.showinfo("Aviso", "Este servidor não possui OTP configurado!")
            except Exception:
                messagebox.showinfo("Aviso", "Erro ao gerar OTP!")

def remover_senha():
    selected = tree.selection()
    if selected:
        idx = int(selected[0])
        resposta = messagebox.askyesno("Remover", "Deseja remover esta senha?", parent=root)
        if resposta:
            senhas.pop(idx)
            salvar_senhas()
            listar_senhas()

ttk.Button(root, text="Cadastrar Senha", command=cadastrar_senha).pack(fill="x", padx=5, pady=2)
ttk.Button(root, text="Configurar OTP para servidor selecionado", command=configurar_otp).pack(fill="x", padx=5, pady=2)

frame_lista = ttk.Frame(root)
frame_lista.pack(fill="both", expand=True, padx=5, pady=2)

tree = ttk.Treeview(frame_lista, columns=("Servidor", "Login", "Senha", "OTP"), show="headings")
tree.heading("Servidor", text="Servidor")
tree.heading("Login", text="Login")
tree.heading("Senha", text="Senha")
tree.heading("OTP", text="OTP")
tree.column("Servidor", anchor="center", width=180)
tree.column("Login", anchor="center", width=180)
tree.column("Senha", anchor="center", width=180)
tree.column("OTP", anchor="center", width=180)
tree.pack(fill="both", expand=True)
tree.bind("<Double-1>", copiar_por_clique)

ttk.Button(root, text="Remover Senha", command=remover_senha).pack(fill="x", padx=5, pady=2)

carregar_senhas()
listar_senhas()
root.mainloop()