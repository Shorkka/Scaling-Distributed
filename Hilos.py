import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
import queue

class DownloadManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Descargas Concurrentes")
        self.root.geometry("600x500")
        
        self.queue = queue.Queue()
        self.downloads = {}
        self.next_id = 1
        
        self.setup_ui()
        self.check_queue()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Controles de entrada
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="URL:").pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(input_frame, width=40)
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.add_button = ttk.Button(input_frame, text="Agregar Descarga", command=self.add_download)
        self.add_button.pack(side=tk.LEFT, padx=5)
        
        # Tabla de descargas
        self.tree = ttk.Treeview(main_frame, columns=('id', 'url', 'progress', 'status'), show='headings')
        self.tree.heading('id', text='ID')
        self.tree.heading('url', text='URL')
        self.tree.heading('progress', text='Progreso')
        self.tree.heading('status', text='Estado')
        self.tree.column('id', width=50)
        self.tree.column('url', width=200)
        self.tree.column('progress', width=100)
        self.tree.column('status', width=150)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Barra de progreso unificada
        self.progress_label = ttk.Label(main_frame, text="Progreso general de descargas activas:")
        self.progress_label.pack(fill=tk.X, padx=5, pady=(10, 0))
        
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate", maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=(0, 10))
        
        # Botones de control
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X)
        
        self.pause_button = ttk.Button(control_frame, text="Pausar", command=self.pause_download, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        self.resume_button = ttk.Button(control_frame, text="Reanudar", command=self.resume_download, state=tk.DISABLED)
        self.resume_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(control_frame, text="Cancelar", command=self.cancel_download, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Barra de estado
        self.status_var = tk.StringVar()
        self.status_var.set("Listo")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, pady=5)
        
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
    
    def add_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor ingrese una URL")
            return
        
        download_id = self.next_id
        self.next_id += 1
        
        self.tree.insert('', tk.END, values=(download_id, url, '0%', 'En cola'), tags=(f'dl_{download_id}',))
        
        self.downloads[download_id] = {
            'url': url,
            'progress': 0,
            'status': 'En cola',
            'paused': False,
            'canceled': False,
            'thread': None
        }
        
        thread = threading.Thread(
            target=self.download_file,
            args=(download_id, url),
            daemon=True
        )
        self.downloads[download_id]['thread'] = thread
        thread.start()
        
        self.url_entry.delete(0, tk.END)
        self.status_var.set(f"Descarga {download_id} agregada a la cola")
        self.update_overall_progress()
    
    def download_file(self, download_id, url):
        try:
            self.downloads[download_id]['status'] = 'Descargando'
            self.queue.put(('update', download_id))
            
            for i in range(1, 101):
                if self.downloads[download_id]['canceled']:
                    self.downloads[download_id]['status'] = 'Cancelado'
                    self.queue.put(('update', download_id))
                    return
                
                while self.downloads[download_id]['paused']:
                    time.sleep(0.1)
                    if self.downloads[download_id]['canceled']:
                        self.downloads[download_id]['status'] = 'Cancelado'
                        self.queue.put(('update', download_id))
                        return
                
                time.sleep(random.uniform(0.05, 0.2))
                
                self.downloads[download_id]['progress'] = i
                self.queue.put(('progress', download_id))
            
            self.downloads[download_id]['status'] = 'Completado'
            self.queue.put(('update', download_id))
            
        except Exception as e:
            self.downloads[download_id]['status'] = f'Error: {str(e)}'
            self.queue.put(('update', download_id))
    
    def check_queue(self):
        try:
            while True:
                msg_type, download_id = self.queue.get_nowait()
                
                if msg_type == 'progress':
                    progress = self.downloads[download_id]['progress']
                    self.update_progress(download_id, progress)
                    self.update_overall_progress()  
                elif msg_type == 'update':
                    self.update_download_status(download_id)
                    self.update_overall_progress()
                
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)
    
    def update_progress(self, download_id, progress):
        for item in self.tree.get_children():
            if int(self.tree.item(item, 'values')[0]) == download_id:  # Conversión aquí
                values = list(self.tree.item(item, 'values'))
                values[2] = f'{progress}%'
                self.tree.item(item, values=values)
                break
    def update_overall_progress(self):
        active_downloads = [d for d in self.downloads.values() if d['status'] in ['Descargando', 'En pausa']]
        
        if not active_downloads:
            self.progress_bar['value'] = 0
            return
        
        total_progress = sum(d['progress'] for d in active_downloads)
        avg_progress = total_progress / len(active_downloads)
        self.progress_bar['value'] = avg_progress
        
        # Actualizar etiqueta para mostrar información más detallada
        self.progress_label.config(text=f"Progreso general ({len(active_downloads)} descargas activas): {avg_progress:.1f}%")
    
    def update_download_status(self, download_id):
        download = self.downloads.get(download_id)
        if not download:
            return
            
        for item in self.tree.get_children():
            if self.tree.item(item, 'values')[0] == download_id:
                values = list(self.tree.item(item, 'values'))
                values[3] = download['status']
                self.tree.item(item, values=values)
                break
    
    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            self.pause_button.config(state=tk.DISABLED)
            self.resume_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
            return
        
        item = selected[0]
        download_id = int(self.tree.item(item, 'values')[0])
        status = self.downloads[download_id]['status']
        
        if status == 'Descargando':
            self.pause_button.config(state=tk.NORMAL)
            self.resume_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.NORMAL)
        elif status == 'En pausa':
            self.pause_button.config(state=tk.DISABLED)
            self.resume_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.NORMAL)
        else:
            self.pause_button.config(state=tk.DISABLED)
            self.resume_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
    
    def pause_download(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        download_id = int(self.tree.item(item, 'values')[0])
        
        self.downloads[download_id]['paused'] = True
        self.downloads[download_id]['status'] = 'En pausa'
        self.queue.put(('update', download_id))
        self.on_tree_select(None)
    
    def resume_download(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        download_id = int(self.tree.item(item, 'values')[0])
        
        self.downloads[download_id]['paused'] = False
        self.downloads[download_id]['status'] = 'Descargando'
        self.queue.put(('update', download_id))
        self.on_tree_select(None)
    
    def cancel_download(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        download_id = int(self.tree.item(item, 'values')[0])
        
        self.downloads[download_id]['canceled'] = True
        self.downloads[download_id]['status'] = 'Cancelado'
        self.queue.put(('update', download_id))
        self.on_tree_select(None)

if __name__ == "__main__":
    root = tk.Tk()
    app = DownloadManager(root)
    root.mainloop()