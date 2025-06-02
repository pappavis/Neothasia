from tkinter import Tk, simpledialog, filedialog, colorchooser, messagebox
import pygame
import json

def choose_color(track_colors):
    Tk().withdraw()
    track_num = simpledialog.askinteger("Track Color", "Enter track number:")
    if track_num is not None and track_num in track_colors:
        color = colorchooser.askcolor(title=f"Choose color for Track {track_num}")
        if color[1] is not None:
            track_colors[track_num] = pygame.Color(color[1])

def export_colors(track_colors):
    Tk().withdraw()
    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, 'w') as f:
            json.dump({k: v.hex for k, v in track_colors.items()}, f)
        messagebox.showinfo("Export Successful", f"Track colors exported to {file_path}")

