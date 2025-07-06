import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ExifTags
from PyPDF2 import PdfReader
import mutagen
import webbrowser
import os
import re

def convert_to_decimal(gps_info):
    """Robust GPS data converter for EXIF dictionaries"""
    try:
        
        lat_ref = gps_info.get(1, 'N').upper()
        lon_ref = gps_info.get(3, 'E').upper()
        lat = gps_info.get(2, (0, 0, 0))
        lon = gps_info.get(4, (0, 0, 0))
        
      
        def to_float(val):
            if isinstance(val, tuple):
                return val[0] / val[1] if val[1] != 0 else 0.0
            if isinstance(val, int):
                return float(val)
            return val
        
       
        lat_deg = to_float(lat[0]) + to_float(lat[1])/60 + to_float(lat[2])/3600
        lon_deg = to_float(lon[0]) + to_float(lon[1])/60 + to_float(lon[2])/3600
        
 
        if lat_ref == 'S': lat_deg = -lat_deg
        if lon_ref == 'W': lon_deg = -lon_deg
        
        return lat_deg, lon_deg
        
    except Exception as e:
        raise ValueError(f"GPS CONVERSION FAILURE: {str(e)}")

class MetaSiphon:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("ARISE METASCAN v1.0")
        self.window.geometry("750x550")
        self.window.configure(bg='#0f0f0f')
        
       
        tk.Label(self.window, text="SELECT TARGET FILE", fg='#00ff00', bg='#0f0f0f', 
                font=("Courier", 16, "bold")).pack(pady=20)
        
        self.btn_frame = tk.Frame(self.window, bg='#0f0f0f')
        self.btn_frame.pack(pady=10)
        
        self.btn_select = tk.Button(self.btn_frame, text="BROWSE FILES", command=self.load_file, 
                                  bg='#222222', fg='#00ff00', font=("Courier", 12), 
                                  width=20, relief='groove')
        self.btn_select.pack(side=tk.LEFT, padx=10)
        
        self.btn_map = tk.Button(self.btn_frame, text="OPEN GOOGLE MAPS", command=self.show_google_map, 
                               bg='#222222', fg='#ff3300', state='disabled', font=("Courier", 12),
                               width=20)
        self.btn_map.pack(side=tk.LEFT, padx=10)
        
      
        self.text_frame = tk.Frame(self.window)
        self.text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.scrollbar = tk.Scrollbar(self.text_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_box = tk.Text(self.text_frame, height=22, width=90, bg='#111111', fg='#00ff00', 
                              font=("Consolas", 10), relief='sunken', yscrollcommand=self.scrollbar.set)
        self.text_box.pack(fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.text_box.yview)
        
      
        self.status_var = tk.StringVar()
        self.status_var.set("SYSTEM: READY | AWAITING TARGET")
        self.status_bar = tk.Label(self.window, textvariable=self.status_var, fg='#00ccff', bg='#0f0f0f',
                                 font=("Courier", 10), anchor='w', relief='sunken', bd=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.gps_data = None
        self.file_path = None
        self.coordinates = None
        
    def update_status(self, message):
        self.status_var.set(f"SYSTEM: {message}")
        self.window.update_idletasks()
        
    def load_file(self):
        self.file_path = filedialog.askopenfilename()
        if not self.file_path:
            return
            
        self.text_box.delete(1.0, tk.END)
        self.gps_data = None
        self.coordinates = None
        self.btn_map.config(state='disabled')
        self.update_status(f"PROCESSING: {os.path.basename(self.file_path)}")
        
        try:
            if self.file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.extract_image_metadata()
            elif self.file_path.lower().endswith('.pdf'):
                self.extract_pdf_metadata()
            elif self.file_path.lower().endswith(('.mp3', '.wav', '.flac')):
                self.extract_audio_metadata()
            elif self.file_path.lower().endswith(('.mp4', '.avi', '.mov')):
                self.extract_video_metadata()
            else:
                self.text_box.insert(tk.END, "[-] UNSUPPORTED FILE TYPE\n")
                self.update_status("[-] UNSUPPORTED FILE TYPE")
        except Exception as e:
            self.text_box.insert(tk.END, f"[SYSTEM FAILURE] {str(e)}\n")
            self.update_status(f"CRITICAL ERROR: {str(e)}")

    def extract_image_metadata(self):
        try:
            img = Image.open(self.file_path)
            exif_data = img._getexif()
            
            if exif_data:
                self.text_box.insert(tk.END, f"[IMAGE METADATA EXTRACTED]\n\n")
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == 'GPSInfo':
                        self.gps_data = value
                        try:
                            self.coordinates = convert_to_decimal(self.gps_data)
                            self.btn_map.config(state='normal')
                            self.text_box.insert(tk.END, f"GPS COORDINATES: {self.coordinates[0]:.6f}, {self.coordinates[1]:.6f}\n")
                        except Exception as e:
                            self.text_box.insert(tk.END, f"[GPS ERROR] {str(e)}\n")
                    self.text_box.insert(tk.END, f"{tag}: {value}\n")
                self.update_status("SUCCESS: IMAGE METADATA EXTRACTED")
            else:
                self.text_box.insert(tk.END, "[WARNING] NO METADATA FOUND IN IMAGE\n")
                self.update_status("WARNING: NO METADATA DETECTED")
        except Exception as e:
            self.text_box.insert(tk.END, f"[IMAGE PROCESSING ERROR] {str(e)}\n")
            self.update_status(f"ERROR: {str(e)}")

    def extract_pdf_metadata(self):
        try:
            with open(self.file_path, 'rb') as f:
                pdf = PdfReader(f)
                info = pdf.metadata
                if info:
                    self.text_box.insert(tk.END, f"[PDF METADATA EXTRACTED]\n\n")
                    for key, value in info.items():
                        self.text_box.insert(tk.END, f"{key[1:]}: {value}\n")
                    self.update_status("SUCCESS: PDF METADATA EXTRACTED")
                else:
                    self.text_box.insert(tk.END, "[WARNING] NO METADATA FOUND IN PDF\n")
                    self.update_status("WARNING: NO METADATA DETECTED")
        except Exception as e:
            self.text_box.insert(tk.END, f"[PDF PROCESSING ERROR] {str(e)}\n")
            self.update_status(f"ERROR: {str(e)}")

    def extract_audio_metadata(self):
        try:
            audio = mutagen.File(self.file_path)
            if audio is not None:
                self.text_box.insert(tk.END, f"[AUDIO METADATA EXTRACTED]\n\n")
                for key, value in audio.items():
                    self.text_box.insert(tk.END, f"{key}: {value}\n")
                self.update_status("SUCCESS: AUDIO METADATA EXTRACTED")
            else:
                self.text_box.insert(tk.END, "[WARNING] NO METADATA FOUND IN AUDIO FILE\n")
                self.update_status("WARNING: NO METADATA DETECTED")
        except Exception as e:
            self.text_box.insert(tk.END, f"[AUDIO PROCESSING ERROR] {str(e)}\n")
            self.update_status(f"ERROR: {str(e)}")

    def extract_video_metadata(self):
        try:
            video = mutagen.File(self.file_path)
            if video is not None:
                self.text_box.insert(tk.END, f"[VIDEO METADATA EXTRACTED]\n\n")
                for key, value in video.items():
                    self.text_box.insert(tk.END, f"{key}: {value}\n")
                self.update_status("SUCCESS: VIDEO METADATA EXTRACTED")
            else:
                self.text_box.insert(tk.END, "[WARNING] NO METADATA FOUND IN VIDEO FILE\n")
                self.update_status("WARNING: NO METADATA DETECTED")
        except Exception as e:
            self.text_box.insert(tk.END, f"[VIDEO PROCESSING ERROR] {str(e)}\n")
            self.update_status(f"ERROR: {str(e)}")

    def show_google_map(self):
        if not self.coordinates:
            messagebox.showerror("Geolocation Error", "No valid coordinates available")
            return
            
        try:
            lat, lon = self.coordinates
        
            maps_url = f"https://www.google.com/maps/place/{lat},{lon}/@{lat},{lon},17z/data=!3m1!1e3"
            webbrowser.open(maps_url)
            self.update_status(f"GEOLOCATION: Opening Google Maps at {lat:.6f}, {lon:.6f}")
        except Exception as e:
            messagebox.showerror("Mapping Error", f"Failed to launch Google Maps: {str(e)}")
            self.update_status(f"GEOLOCATION FAILURE: {str(e)}")

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    MetaSiphon().run()