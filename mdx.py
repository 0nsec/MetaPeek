import tkinter as tk
from tkinter import filedialog
from PIL import Image, ExifTags
from PyPDF2 import PdfReader
import mutagen
import folium
import webbrowser
import os

class MetaSiphon:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("META-SIPHON v1.0")
        self.window.geometry("700x500")
        self.window.configure(bg='#0f0f0f')
        

        tk.Label(self.window, text="SELECT TARGET FILE", fg='#00ff00', bg='#0f0f0f', font=("Courier", 14)).pack(pady=20)
        
        self.btn_select = tk.Button(self.window, text="BROWSE FILES", command=self.load_file, 
                                  bg='#222222', fg='#00ff00', font=("Courier", 12), relief='groove')
        self.btn_select.pack(pady=10)
        
        self.btn_map = tk.Button(self.window, text="OPEN LOCATION MAP", command=self.show_map, 
                               bg='#222222', fg='#ff0000', state='disabled', font=("Courier", 12))
        self.btn_map.pack(pady=10)
        
        self.text_box = tk.Text(self.window, height=20, width=80, bg='#111111', fg='#00ff00', 
                              font=("Consolas", 10), relief='sunken')
        self.text_box.pack(pady=20)
        
        self.gps_data = None
        self.file_path = None
        
    def load_file(self):
        self.file_path = filedialog.askopenfilename()
        if not self.file_path:
            return
            
        self.text_box.delete(1.0, tk.END)
        self.gps_data = None
        self.btn_map.config(state='disabled')
        
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
                self.text_box.insert(tk.END, "[ERROR] UNSUPPORTED FILE TYPE\n")
        except Exception as e:
            self.text_box.insert(tk.END, f"[SYSTEM FAILURE] {str(e)}\n")

    def extract_image_metadata(self):
        img = Image.open(self.file_path)
        exif_data = img._getexif()
        
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if tag == 'GPSInfo':
                    self.gps_data = value
                    self.btn_map.config(state='normal')
                self.text_box.insert(tk.END, f"{tag}: {value}\n")
        else:
            self.text_box.insert(tk.END, "[WARNING] NO METADATA FOUND IN IMAGE\n")

    def extract_pdf_metadata(self):
        with open(self.file_path, 'rb') as f:
            pdf = PdfReader(f)
            info = pdf.metadata
            for key, value in info.items():
                self.text_box.insert(tk.END, f"{key[1:]}: {value}\n")

    def extract_audio_metadata(self):
        audio = mutagen.File(self.file_path)
        for key, value in audio.items():
            self.text_box.insert(tk.END, f"{key}: {value}\n")

    def extract_video_metadata(self):
        video = mutagen.File(self.file_path)
        for key, value in video.items():
            self.text_box.insert(tk.END, f"{key}: {value}\n")

    def show_map(self):
        if not self.gps_data:
            return

        lat_data = self.gps_data[2]
        lon_data = self.gps_data[4]
        
        lat = lat_data[0] + lat_data[1]/60 + lat_data[2]/3600
        lon = lon_data[0] + lon_data[1]/60 + lon_data[2]/3600
        
        if self.gps_data[1] == 'S': lat = -lat
        if self.gps_data[3] == 'W': lon = -lon
        

        map_obj = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker([lat, lon], tooltip="EXIF LOCATION").add_to(map_obj)
        map_path = os.path.join(os.getcwd(), "target_location.html")
        map_obj.save(map_path)
        webbrowser.open(f"file://{map_path}")

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    MetaSiphon().run()