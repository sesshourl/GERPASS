"""Gerenciador de senhas com criptografia e suporte a OTP."""

import json
import os
import tkinter as tk
from tkinter import messagebox, ttk

import pyotp
import pyperclip
from cryptography.fernet import Fernet, InvalidToken

APPDATA = os.getenv("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
GERPASS_DIR = os.path.join(APPDATA, "GERPASS")
os.makedirs(GERPASS_DIR, exist_ok=True)
ARQUIVO = os.path.join(GERPASS_DIR, "senhas.json.enc")
KEY_FILE = os.path.join(GERPASS_DIR, "key.key")
SETTINGS_FILE = os.path.join(GERPASS_DIR, "settings.json")


def load_or_create_key():
    """Load an existing encryption key or create a new one.

    Returns:
        bytes: The secret key used for Fernet encryption.
    """
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as file:
            file.write(key)
        return key

    with open(KEY_FILE, "rb") as file:
        return file.read()


class GerpassApp:
    """Application class for the Gerpass password manager."""

    def __init__(self):
        """Initialize the application state, encryption, and main window."""
        self.fernet = Fernet(load_or_create_key())
        self.senhas = []
        self.root = tk.Tk()
        self.root.title("Gerenciador de Senhas")
        style = ttk.Style(self.root)
        style.theme_use("alt")
        self.root.geometry("800x600")
        self.load_window_geometry()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.tree = None
        self._temp_message_window = None

    def show_temporary_message(self, title, message, duration_ms=3000):
        """Show a temporary notification window that closes itself."""
        if self._temp_message_window and self._temp_message_window.winfo_exists():
            self._temp_message_window.destroy()

        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        tk.Label(dialog, text=message, padx=20, pady=10).pack()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - \
            (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - \
            (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        dialog.after(duration_ms, dialog.destroy)
        self._temp_message_window = dialog

    def load_window_geometry(self):
        """Load saved window geometry from disk, if available."""
        if not os.path.exists(SETTINGS_FILE):
            return

        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
                settings = json.load(file)
            geometry = settings.get("window_geometry")
            if geometry:
                self.root.geometry(geometry)
        except (json.JSONDecodeError, OSError):
            pass

    def save_window_geometry(self):
        """Save the current window geometry to disk."""
        geometry = self.root.winfo_geometry()
        settings = {"window_geometry": geometry}
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
                json.dump(settings, file, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def on_close(self):
        """Handle window close by saving geometry and exiting cleanly."""
        self.save_window_geometry()
        self.root.destroy()

    def ask_input(self, title, prompt, show=None):
        """Show an input dialog and return the entered value.

        Args:
            title (str): Dialog title.
            prompt (str): Prompt text displayed inside the dialog.
            show (str, optional): Masking character for password input.

        Returns:
            str | None: The user input, or None if canceled.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text=prompt).pack(padx=10, pady=10)
        entry = tk.Entry(dialog, show=show) if show else tk.Entry(dialog)
        entry.pack(padx=10, pady=10)
        entry.focus_force()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - \
            (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - \
            (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        result = []

        def on_ok():
            result.append(entry.get())
            dialog.destroy()

        entry.bind("<Return>", lambda _: on_ok())
        tk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
        dialog.wait_window()
        return result[0] if result else None

    def carregar_senhas(self):
        """Load saved password records from the encrypted storage file."""
        if not os.path.exists(ARQUIVO):
            self.senhas.clear()
            return

        try:
            with open(ARQUIVO, "rb") as file:
                encrypted = file.read()
            data = self.fernet.decrypt(encrypted)
            carregadas = json.loads(data.decode("utf-8"))
            for item in carregadas:
                item.setdefault("pin", "")
            self.senhas.clear()
            self.senhas.extend(carregadas)
        except (json.JSONDecodeError, IOError, InvalidToken):
            self.senhas.clear()

    def salvar_senhas(self):
        """Encrypt and save the current password list to disk."""
        try:
            data = json.dumps(self.senhas, ensure_ascii=False,
                              indent=2).encode("utf-8")
            encrypted = self.fernet.encrypt(data)
            with open(ARQUIVO, "wb") as file:
                file.write(encrypted)
        except (TypeError, ValueError, OSError) as error:
            messagebox.showerror(
                "Erro", f"Erro ao salvar senhas: {error}", parent=self.root)

    def gerar_otp(self, secret):
        """Generate a one-time password using the configured secret."""
        try:
            return pyotp.TOTP(secret).now()
        except (ValueError, TypeError):
            return ""

    def listar_senhas(self):
        """Refresh the UI list with the currently loaded passwords."""
        self.tree.delete(*self.tree.get_children())
        for idx, item in enumerate(self.senhas):
            otp = self.gerar_otp(item.get("otp_secret")) if item.get(
                "otp_secret") else ""
            self.tree.insert("", "end", iid=idx, values=(
                item["Servidor"], item["usuario"], item["senha"], item.get("pin", ""), otp))

    def cadastrar_senha(self):
        """Collect new password details from the user and save them."""
        servidor = self.ask_input("Servidor", "Nome do servidor:")
        usuario = self.ask_input("Usuário", "Nome do usuário:")
        senha = self.ask_input("Senha", "Digite a senha:", show="*")
        pin = self.ask_input("PIN", "Digite o código de acesso:", show="*")
        if not (servidor and usuario and senha and pin):
            return

        self.senhas.append({
            "Servidor": servidor,
            "usuario": usuario,
            "senha": "*" * len(senha),
            "senha_real": senha,
            "otp_secret": "",
            "pin": pin
        })
        self.salvar_senhas()
        self.listar_senhas()
        messagebox.showinfo("Sucesso", "Senha cadastrada!", parent=self.root)

    def get_selected_index(self):
        """Return the currently selected row index in the password list."""
        selected = self.tree.selection()
        return int(selected[0]) if selected else None

    def configurar_otp(self):
        """Configure an OTP secret for the selected password entry."""
        idx = self.get_selected_index()
        if idx is None:
            return

        otp_secret = self.ask_input(
            "OTP Secret", "Cole aqui o segredo OTP fornecido pelo site:")
        if not otp_secret:
            return

        self.senhas[idx]["otp_secret"] = otp_secret
        self.salvar_senhas()
        self.listar_senhas()
        messagebox.showinfo("Sucesso", "OTP configurado!", parent=self.root)

    def remover_senha(self):
        """Remove the selected password entry from storage and UI."""
        idx = self.get_selected_index()
        if idx is None:
            return

        if not messagebox.askyesno("Confirmar", "Remover a senha selecionada?", parent=self.root):
            return

        self.senhas.pop(idx)
        self.salvar_senhas()
        self.listar_senhas()
        messagebox.showinfo("Sucesso", "Senha removida!", parent=self.root)

    def configurar_pin(self):
        """Configure the PIN for the selected password entry."""
        idx = self.get_selected_index()
        if idx is None:
            return

        pin = self.ask_input(
            "Configurar PIN", "Digite o código de acesso:", show="*")
        if not pin:
            return

        self.senhas[idx]["pin"] = pin
        self.salvar_senhas()
        self.listar_senhas()
        messagebox.showinfo("Sucesso", "PIN configurado!", parent=self.root)

    def copiar_por_clique(self, event):
        """Copy the value from the clicked table cell to the clipboard."""
        item_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item_id or not col:
            return

        idx = int(item_id)
        if col == "#1":
            pyperclip.copy(self.senhas[idx]["Servidor"])
            self.show_temporary_message(
                "Copiado", "Servidor copiado para área de transferência!")
        elif col == "#2":
            pyperclip.copy(self.senhas[idx]["usuario"])
            self.show_temporary_message(
                "Copiado", "Login copiado para área de transferência!")
        elif col == "#3":
            pyperclip.copy(self.senhas[idx]["senha_real"])
            self.show_temporary_message(
                "Copiado", "Senha copiada para área de transferência!")
        elif col == "#4":
            pyperclip.copy(self.senhas[idx].get("pin", ""))
            self.show_temporary_message(
                "Copiado", "PIN copiado para área de transferência!")
        elif col == "#5":
            otp = self.gerar_otp(self.senhas[idx].get("otp_secret"))
            if otp:
                pyperclip.copy(otp)
                self.show_temporary_message(
                    "Copiado", "OTP copiado para área de transferência!")
            else:
                self.show_temporary_message(
                    "Aviso", "Este servidor não possui OTP configurado!")

    def configurar_interface(self):
        """Build the main application interface and wire widget callbacks."""
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=5, pady=2)

        ttk.Button(button_frame, text="Configurar Conta", command=self.cadastrar_senha).pack(
            fill="x", pady=2)

        otp_pin_frame = ttk.Frame(self.root)
        otp_pin_frame.pack(fill="x", padx=5, pady=2)
        ttk.Button(otp_pin_frame, text="Configurar OTP",
                   command=self.configurar_otp).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(otp_pin_frame, text="Configurar PIN",
                   command=self.configurar_pin).pack(side="left", fill="x", expand=True, padx=2)

        frame_lista = ttk.Frame(self.root)
        frame_lista.pack(fill="both", expand=True, padx=5, pady=2)

        self.tree = ttk.Treeview(frame_lista, columns=(
            "Servidor", "Login", "Senha", "PIN", "OTP"), show="headings")
        self.tree.heading("Servidor", text="Servidor")
        self.tree.heading("Login", text="Login")
        self.tree.heading("Senha", text="Senha")
        self.tree.heading("PIN", text="PIN")
        self.tree.heading("OTP", text="OTP")
        self.tree.column("Servidor", anchor="center", width=140)
        self.tree.column("Login", anchor="center", width=140)
        self.tree.column("Senha", anchor="center", width=120)
        self.tree.column("PIN", anchor="center", width=100)
        self.tree.column("OTP", anchor="center", width=120)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.copiar_por_clique)

        ttk.Button(self.root, text="Remover Senha", command=self.remover_senha).pack(
            fill="x", padx=5, pady=2)

    def run(self):
        """Run the application by loading data and starting the main loop."""
        self.configurar_interface()
        self.carregar_senhas()
        self.listar_senhas()
        self.root.mainloop()


def main():
    """Create the application instance and start it."""
    GerpassApp().run()


if __name__ == "__main__":
    main()
