import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ExifTags
from PIL.ExifTags import GPSTAGS
import os
import json
import webbrowser
from datetime import timedelta

try:
    from PyPDF2 import PdfReader
except ImportError:
    print("Missing PyPDF2. Please install with: pip install PyPDF2")
    exit()

try:
    import mutagen
except ImportError:
    print("Missing mutagen. Please install with: pip install mutagen")
    exit()


def parse_dms(dms):
    return dms[0][0] / dms[0][1] + dms[1][0] / (dms[1][1] * 60) + dms[2][0] / (dms[2][1] * 3600)

def convert_to_decimal(gps_info):
    try:
        lat = parse_dms(gps_info.get("GPSLatitude"))
        lon = parse_dms(gps_info.get("GPSLongitude"))

        if gps_info.get("GPSLatitudeRef", 'N') == 'S':
            lat = -lat
        if gps_info.get("GPSLongitudeRef", 'E') == 'W':
            lon = -lon

        return round(lat, 6), round(lon, 6)
    except Exception as e:
        raise ValueError(f"GPS conversion error: {e}")

def get_exif_gps_info(exif_data):
    gps_info = {}
    for tag_id, value in exif_data.items():
        tag = ExifTags.TAGS.get(tag_id, tag_id)
        if tag == 'GPSInfo':
            for key in value.keys():
                sub_tag = GPSTAGS.get(key, key)
                gps_info[sub_tag] = value[key]
    return gps_info

class MetaSiphon:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("MDX v1.1")
        self.window.geometry("850x650")
        self.window.configure(bg='#0f0f0f')
        self.window.minsize(800, 600)

        self.style = ttk.Style()
        self.style.configure('TFrame', background='#0f0f0f')
        self.style.configure('TButton', font=('Courier', 11), padding=5)
        self.style.configure('TLabel', background='#0f0f0f', foreground='#00ff00')
        self.style.configure('Status.TLabel', font=('Courier', 9), foreground='#00ccff')

        header_frame = ttk.Frame(self.window)
        header_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(header_frame, text="MDX v1.1", font=("Courier", 18, "bold")).pack(pady=10)
        ttk.Label(header_frame, text="SELECT TARGET FILE FOR METADATA EXTRACTION", font=("Courier", 11)).pack()

        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(pady=15, fill=tk.X, padx=50)

        self.btn_select = ttk.Button(btn_frame, text="BROWSE FILES", command=self.load_file)
        self.btn_select.pack(side=tk.LEFT, expand=True, padx=10)

        self.btn_export = ttk.Button(btn_frame, text="EXPORT METADATA", command=self.export_metadata, state='disabled')
        self.btn_export.pack(side=tk.LEFT, expand=True, padx=10)

        self.btn_map = ttk.Button(btn_frame, text="OPEN GOOGLE MAPS", command=self.show_google_map, state='disabled')
        self.btn_map.pack(side=tk.LEFT, expand=True, padx=10)

        display_frame = ttk.Frame(self.window)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(display_frame, columns=('Value'), selectmode='extended')
        self.tree.heading('#0', text='Metadata Field')
        self.tree.heading('Value', text='Value')
        self.tree.column('#0', width=250, minwidth=200)
        self.tree.column('Value', width=400, minwidth=300)

        vsb = ttk.Scrollbar(display_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(display_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_var = tk.StringVar()
        self.status_var.set("STATUS: Ready | Awaiting target file")
        status_bar = ttk.Label(self.window, textvariable=self.status_var, style='Status.TLabel', relief='sunken', padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.file_path = None
        self.coordinates = None
        self.metadata = {}

    def update_status(self, message):
        self.status_var.set(f"STATUS: {message}")
        self.window.update_idletasks()

    def clear_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def add_metadata(self, key, value):
        if isinstance(value, list):
            value = ', '.join(map(str, value))
        self.tree.insert('', 'end', text=key, values=(value,))

    def load_file(self):
        file_types = (
            ('All Supported Files', '*.jpg *.jpeg *.png *.pdf *.mp3 *.wav *.flac *.mp4 *.avi *.mov'),
            ('Images', '*.jpg *.jpeg *.png'),
            ('PDFs', '*.pdf'),
            ('Audio', '*.mp3 *.wav *.flac'),
            ('Video', '*.mp4 *.avi *.mov'),
            ('All Files', '*.*')
        )

        self.file_path = filedialog.askopenfilename(filetypes=file_types)
        if not self.file_path:
            return

        self.clear_treeview()
        self.coordinates = None
        self.metadata = {}
        self.btn_map.config(state='disabled')
        self.btn_export.config(state='disabled')

        filename = os.path.basename(self.file_path)
        self.update_status(f"Processing: {filename}...")

        try:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.extract_image_metadata()
            elif filename.lower().endswith('.pdf'):
                self.extract_pdf_metadata()
            elif filename.lower().endswith(('.mp3', '.wav', '.flac')):
                self.extract_audio_metadata()
            else:
                self.add_metadata('Error', 'Unsupported file type')
                self.update_status("Error: Unsupported file type")
                return

            self.btn_export.config(state='normal')
            self.update_status(f"Metadata extracted: {len(self.metadata)} fields found")

        except Exception as e:
            self.add_metadata('System Error', str(e))
            self.update_status(f"Critical Error: {str(e)}")

    def extract_image_metadata(self):
        try:
            img = Image.open(self.file_path)
            exif_data = img._getexif() or {}
            self.metadata['File Type'] = img.format
            self.metadata['Dimensions'] = f"{img.width} x {img.height} px"
            self.metadata['Color Mode'] = img.mode

            gps_info = get_exif_gps_info(exif_data)
            if gps_info:
                try:
                    self.coordinates = convert_to_decimal(gps_info)
                    self.metadata['GPS Coordinates'] = f"{self.coordinates[0]}, {self.coordinates[1]}"
                    self.btn_map.config(state='normal')
                except Exception as gps_error:
                    self.metadata['GPS Error'] = str(gps_error)

            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if isinstance(value, bytes):
                    try:
                        value = value.decode()
                    except:
                        value = str(value)
                self.metadata[tag] = value

            for key, value in self.metadata.items():
                self.add_metadata(key, value)

            self.update_status(f"Image metadata extracted: {len(self.metadata)} fields")

        except Exception as e:
            self.add_metadata('Processing Error', str(e))
            self.update_status(f"Image Error: {str(e)}")

    def extract_pdf_metadata(self):
        try:
            with open(self.file_path, 'rb') as f:
                pdf = PdfReader(f)
                info = pdf.metadata or {}

                self.metadata['Pages'] = len(pdf.pages)
                self.metadata['Encrypted'] = pdf.is_encrypted

                for key, value in info.items():
                    self.metadata[key.strip('/')] = value

                for key, value in self.metadata.items():
                    self.add_metadata(key, value)

                self.update_status(f"PDF metadata extracted: {len(self.metadata)} fields")

        except Exception as e:
            self.add_metadata('Processing Error', str(e))
            self.update_status(f"PDF Error: {str(e)}")

    def extract_audio_metadata(self):
        try:
            audio = mutagen.File(self.file_path)
            if audio is None:
                self.add_metadata('Warning', 'No metadata found')
                self.update_status("Audio: No metadata detected")
                return

            self.metadata['Format'] = audio.mime[0] if audio.mime else 'Unknown'
            self.metadata['Bitrate'] = f"{audio.info.bitrate} kbps" if hasattr(audio.info, 'bitrate') else 'N/A'
            self.metadata['Duration'] = str(timedelta(seconds=int(audio.info.length))) if hasattr(audio.info, 'length') else 'N/A'

            for key, value in audio.items():
                if isinstance(value, list) and len(value) == 1:
                    value = value[0]
                self.metadata[key] = value

            for key, value in self.metadata.items():
                self.add_metadata(key, value)

            self.update_status(f"Audio metadata extracted: {len(self.metadata)} fields")

        except Exception as e:
            self.add_metadata('Processing Error', str(e))
            self.update_status(f"Audio Error: {str(e)}")

    def show_google_map(self):
        if not self.coordinates:
            messagebox.showwarning("Location Error", "No GPS coordinates available")
            return

        try:
            lat, lon = self.coordinates
            maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            webbrowser.open(maps_url)
            self.update_status(f"Location: Opened Google Maps at {lat}, {lon}")
        except Exception as e:
            messagebox.showerror("Mapping Error", f"Failed to open maps: {str(e)}")
            self.update_status(f"Map Error: {str(e)}")

    def export_metadata(self):
        if not self.metadata:
            messagebox.showwarning("Export Error", "No metadata to export")
            return

        export_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*"))
        )

        if not export_path:
            return

        try:
            if export_path.endswith('.json'):
                with open(export_path, 'w') as f:
                    json.dump(self.metadata, f, indent=4)
            else:
                with open(export_path, 'w') as f:
                    for key, value in self.metadata.items():
                        f.write(f"{key}: {value}\n")

            self.update_status(f"Metadata exported to {os.path.basename(export_path)}")
            messagebox.showinfo("Export Successful", "Metadata exported successfully")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
            self.update_status(f"Export Error: {str(e)}")

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = MetaSiphon()
    app.run()
