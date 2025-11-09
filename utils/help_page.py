import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Canvas
from datetime import datetime
from utils.path_utils import resource_path
from PIL import Image, ImageTk
import io

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("[HELP] PyMuPDF not available. PDF viewer will fall back to external viewer.")

class HelpPage(tk.Frame):
    """Modern Help page with integrated PDF viewer.
    
    Features:
    - Direct PDF viewing inside the application
    - Page navigation (Previous/Next)
    - Language selection (English/French)
    - Zoom controls
    - Page counter
    - Fallback to external viewer if PyMuPDF unavailable
    """
    
    def __init__(self, parent, app):
        super().__init__(parent, bg="#009AA5")
        self.app = app
        self.current_pdf = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = 1.0
        self.pdf_document = None
        
        # Check if we can use integrated viewer
        self.use_integrated_viewer = PYMUPDF_AVAILABLE
        
        if self.use_integrated_viewer:
            self._create_integrated_viewer()
        else:
            self._create_fallback_viewer()
    
    def _create_integrated_viewer(self):
        """Create integrated PDF viewer with PyMuPDF."""
        # Header
        header_frame = tk.Frame(self, bg="#004d4d")
        header_frame.pack(fill="x", pady=0)
        
        header = tk.Label(
            header_frame, 
            text="❓ Help & User Guide", 
            font=("Arial", 20, "bold"), 
            bg="#004d4d", 
            fg="white"
        )
        header.pack(pady=15)
        
        sub = tk.Label(
            header_frame,
            text="Complete user manual with screenshots",
            font=("Arial", 11),
            bg="#004d4d",
            fg="#cccccc"
        )
        sub.pack(pady=(0, 15))
        
        # Find available PDFs
        self.english_pdf = self._find_pdf("English")
        self.french_pdf = self._find_pdf("French")
        
        # Main content frame (holds either welcome screen OR PDF viewer)
        self.main_content_frame = tk.Frame(self, bg="#009AA5")
        self.main_content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Show welcome screen initially
        self._show_welcome_screen()
    
    
    def _show_welcome_screen(self):
        """Display the welcome/language selection screen."""
        # Close PDF document if open
        if self.pdf_document:
            try:
                self.pdf_document.close()
                self.pdf_document = None
                self.current_pdf = None
                self.current_page = 0
                self.total_pages = 0
            except Exception:
                pass
        
        # Clear main content frame
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()
        
        # Main white content box
        content_frame = tk.Frame(self.main_content_frame, bg="#ffffff", relief="ridge", borderwidth=3)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title with icon
        title_frame = tk.Frame(content_frame, bg="#ffffff")
        title_frame.pack(pady=(40, 10))
        
        tk.Label(
            title_frame,
            text="📚 BITSS VWAR User Manual",
            font=("Arial", 28, "bold"),
            bg="#ffffff",
            fg="#004d4d"
        ).pack()
        
        # Subtitle
        tk.Label(
            content_frame,
            text="Complete guide with step-by-step instructions and screenshots",
            font=("Arial", 13),
            bg="#ffffff",
            fg="#666666"
        ).pack(pady=(5, 3))
        
        tk.Label(
            content_frame,
            text="Available in English and French",
            font=("Arial", 13),
            bg="#ffffff",
            fg="#666666"
        ).pack(pady=(0, 40))
        
        # Language buttons
        buttons_frame = tk.Frame(content_frame, bg="#ffffff")
        buttons_frame.pack(pady=20)
        
        # English button
        if self.english_pdf:
            english_btn = tk.Button(
                buttons_frame,
                text="📄 Open English User Manual",
                command=lambda: self._load_pdf(self.english_pdf, "English"),
                bg="#007777",
                fg="white",
                font=("Arial", 14, "bold"),
                padx=40,
                pady=15,
                relief="raised",
                cursor="hand2",
                borderwidth=3,
                activebackground="#005555",
                activeforeground="white"
            )
            english_btn.pack(pady=10)
            
            # File info
            file_size = self._get_file_size(self.english_pdf)
            tk.Label(
                buttons_frame,
                text=f"File: English copy of BITSS VWAR USER Manual.pdf ({file_size})",
                font=("Arial", 9),
                bg="#ffffff",
                fg="#999999"
            ).pack(pady=(0, 20))
        
        # French button
        if self.french_pdf:
            french_btn = tk.Button(
                buttons_frame,
                text="📄 Ouvrir le Manuel Utilisateur Français",
                command=lambda: self._load_pdf(self.french_pdf, "French"),
                bg="#007777",
                fg="white",
                font=("Arial", 14, "bold"),
                padx=40,
                pady=15,
                relief="raised",
                cursor="hand2",
                borderwidth=3,
                activebackground="#005555",
                activeforeground="white"
            )
            french_btn.pack(pady=10)
            
            # File info
            file_size = self._get_file_size(self.french_pdf)
            tk.Label(
                buttons_frame,
                text=f"Fichier: French copy of BITSS VWAR USER Manual.pdf ({file_size})",
                font=("Arial", 9),
                bg="#ffffff",
                fg="#999999"
            ).pack(pady=(0, 20))
        
        # Warning if no PDFs found
        if not self.english_pdf and not self.french_pdf:
            tk.Label(
                buttons_frame,
                text="⚠️ User manual PDFs not found\n"
                     "Please contact support for assistance",
                font=("Arial", 12, "bold"),
                bg="#ffffff",
                fg="#cc0000",
                justify="center"
            ).pack(pady=30)
        
        # Separator line
        separator = tk.Frame(content_frame, bg="#cccccc", height=2)
        separator.pack(fill="x", padx=60, pady=(40, 30))
        
        # Footer section
        footer_section = tk.Frame(content_frame, bg="#ffffff")
        footer_section.pack(pady=(10, 30))
        
        tk.Label(
            footer_section,
            text="📞 Need More Help?",
            font=("Arial", 16, "bold"),
            bg="#ffffff",
            fg="#004d4d"
        ).pack(pady=(0, 15))
        
        tk.Label(
            footer_section,
            text="Need help? 📧 support@bobosohomail.com | 🌐 www.bitss.one",
            font=("Arial", 11),
            bg="#ffffff",
            fg="#666666"
        ).pack()
    
    def _show_pdf_viewer(self):
        """Display the PDF viewer interface (replaces welcome screen)."""
        # Clear main content frame
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()
        
        # Control panel at top
        control_frame = tk.Frame(self.main_content_frame, bg="#ffffff", relief="ridge", borderwidth=2)
        control_frame.pack(fill="x", padx=0, pady=(0, 5))
        
        # Back button (left side)
        back_btn = tk.Button(
            control_frame,
            text="◀ Back to Language Selection",
            command=self._show_welcome_screen,
            bg="#555555",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=5,
            relief="raised",
            cursor="hand2"
        )
        back_btn.pack(side="left", padx=10, pady=10)
        
        # Separator
        tk.Frame(control_frame, bg="#cccccc", width=2, height=30).pack(side="left", padx=5)
        
        # Selected language label (left side) - will be updated when PDF loads
        self.selected_lang_frame = tk.Frame(control_frame, bg="#ffffff")
        self.selected_lang_frame.pack(side="left", padx=10, pady=10)
        
        self.selected_lang_label = tk.Label(
            self.selected_lang_frame,
            text="Selected Language: None",
            font=("Arial", 11, "bold"),
            bg="#ffffff",
            fg="#004d4d"
        )
        self.selected_lang_label.pack(side="left")
        
        # Page navigation (right side)
        self.nav_frame = tk.Frame(control_frame, bg="#ffffff")
        self.nav_frame.pack(side="right", padx=10)
        
        self.prev_btn = tk.Button(
            self.nav_frame,
            text="◀ Previous",
            command=self._previous_page,
            bg="#009AA5",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
            state="disabled"
        )
        self.prev_btn.pack(side="left", padx=5)
        
        self.page_label = tk.Label(
            self.nav_frame,
            text="No PDF loaded",
            font=("Arial", 10, "bold"),
            bg="#ffffff",
            fg="#004d4d"
        )
        self.page_label.pack(side="left", padx=10)
        
        self.next_btn = tk.Button(
            self.nav_frame,
            text="Next ▶",
            command=self._next_page,
            bg="#009AA5",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
            state="disabled"
        )
        self.next_btn.pack(side="left", padx=5)
        
        # PDF canvas with scrollbar
        canvas_frame = tk.Frame(self.main_content_frame, bg="#ffffff", relief="sunken", borderwidth=2)
        canvas_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(canvas_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Canvas for PDF rendering
        self.pdf_canvas = Canvas(
            canvas_frame,
            bg="#e0e0e0",
            yscrollcommand=scrollbar.set,
            highlightthickness=0
        )
        self.pdf_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.pdf_canvas.yview)
        
        # Re-render current page when canvas is resized (fixes initial zero-width issues)
        self.pdf_canvas.bind("<Configure>", self._on_canvas_configure)

        # Bind mouse wheel
        self.pdf_canvas.bind("<MouseWheel>", self._on_mousewheel)
    
    def _show_welcome_message(self):
        """Display welcome message on PDF canvas (deprecated - now uses _show_welcome_screen)."""
        if not hasattr(self, 'pdf_canvas'):
            return
            
        self.pdf_canvas.delete("all")
        
        canvas_width = self.pdf_canvas.winfo_width() or 800
        canvas_height = self.pdf_canvas.winfo_height() or 600
        
        # Center text
        x = canvas_width // 2
        y = canvas_height // 2 - 50
        
        self.pdf_canvas.create_text(
            x, y,
            text="📚 BITSS VWAR User Manual",
            font=("Arial", 24, "bold"),
            fill="#004d4d"
        )
        
        self.pdf_canvas.create_text(
            x, y + 50,
            text="Select a language above to view the user guide",
            font=("Arial", 14),
            fill="#555555"
        )
        
        canvas_width = self.pdf_canvas.winfo_width() or 800
        canvas_height = self.pdf_canvas.winfo_height() or 600
        
        # Center text
        x = canvas_width // 2
        y = canvas_height // 2 - 50
        
        self.pdf_canvas.create_text(
            x, y,
            text="📚 BITSS VWAR User Manual",
            font=("Arial", 24, "bold"),
            fill="#004d4d"
        )
        
        self.pdf_canvas.create_text(
            x, y + 50,
            text="Select a language above to view the user guide",
            font=("Arial", 14),
            fill="#555555"
        )
    
    def _load_pdf(self, pdf_path, language):
        """Load and display PDF file.
        
        Args:
            pdf_path: Full path to PDF file
            language: Language name for display
        """
        try:
            if not os.path.exists(pdf_path):
                messagebox.showerror(
                    "File Not Found",
                    f"The {language} user manual could not be found:\n{pdf_path}"
                )
                return
            
            # Close previous PDF if open
            if self.pdf_document:
                self.pdf_document.close()
            
            # Show PDF viewer interface (if not already shown)
            if not hasattr(self, 'pdf_canvas') or not self.pdf_canvas.winfo_exists():
                self._show_pdf_viewer()
            
            # Open new PDF
            self.pdf_document = fitz.open(pdf_path)
            self.current_pdf = pdf_path
            self.current_page = 0
            self.total_pages = len(self.pdf_document)
            
            # Update UI
            self.page_label.config(text=f"Page 1 / {self.total_pages}")
            self.prev_btn.config(state="disabled")
            self.next_btn.config(state="normal" if self.total_pages > 1 else "disabled")
            
            # Update selected language label
            if hasattr(self, 'selected_lang_label'):
                flag = "🇬🇧" if language == "English" else "🇫🇷"
                self.selected_lang_label.config(text=f"Selected Language: {flag} {language}")
            
            # Render first page
            # Make sure canvas size is calculated before rendering
            try:
                self.pdf_canvas.update_idletasks()
            except Exception:
                pass
            self._render_page()
            
            print(f"[HELP] Loaded {language} PDF: {pdf_path} ({self.total_pages} pages)")
            
        except Exception as e:
            messagebox.showerror(
                "Error Loading PDF",
                f"Failed to load {language} user manual:\n{str(e)}"
            )
            print(f"[HELP] Error loading PDF: {e}")
    
    def _render_page(self):
        """Render current PDF page to canvas."""
        if not self.pdf_document:
            return
        
        try:
            # Get page
            page = self.pdf_document[self.current_page]
            
            # Calculate zoom to fit canvas width
            canvas_width = self.pdf_canvas.winfo_width()
            # If the canvas hasn't been fully laid out yet winfo_width() may return 0 or small values.
            # Use a sensible minimum to avoid negative/zero target widths which cause PIL/fitz errors.
            if not canvas_width or canvas_width < 200:
                # try to get parent width as a fallback
                try:
                    canvas_width = self.winfo_width() or 800
                except Exception:
                    canvas_width = 800
            canvas_width = max(canvas_width, 200)

            # Get page pixmap at higher resolution, then scale to fit canvas
            mat = fitz.Matrix(2.0, 2.0)  # High resolution rendering
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Resize to fit canvas width (with padding) - ensure positive sizes
            target_width = max(canvas_width - 40, 100)
            ratio = target_width / img.width
            new_height = max(int(img.height * ratio), 100)
            img = img.resize((int(target_width), int(new_height)), Image.Resampling.LANCZOS)
            
            # Convert to Tkinter PhotoImage
            self.current_image = ImageTk.PhotoImage(img)
            
            # Clear canvas and display image
            self.pdf_canvas.delete("all")
            
            # Center image horizontally
            x = canvas_width // 2
            self.pdf_canvas.create_image(x, 20, anchor="n", image=self.current_image)
            
            # Update scroll region
            self.pdf_canvas.config(scrollregion=(0, 0, canvas_width, new_height + 40))
            
            # Scroll to top
            self.pdf_canvas.yview_moveto(0)
            
        except Exception as e:
            # Common cause: negative/zero dimensions when the canvas is not yet sized.
            print(f"[HELP] Error rendering page: {e}")
            messagebox.showerror("Rendering Error", f"Failed to render page:\n{str(e)}")
    
    def _previous_page(self):
        """Navigate to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._render_page()
            self._update_navigation()
    
    def _next_page(self):
        """Navigate to next page."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._render_page()
            self._update_navigation()
    
    def _update_navigation(self):
        """Update navigation button states and page label."""
        self.page_label.config(text=f"Page {self.current_page + 1} / {self.total_pages}")
        
        # Update button states
        self.prev_btn.config(state="normal" if self.current_page > 0 else "disabled")
        self.next_btn.config(state="normal" if self.current_page < self.total_pages - 1 else "disabled")
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.pdf_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_canvas_configure(self, event):
        """Handle canvas resize events. Re-render the current page so the PDF fits the new size."""
        # Only re-render if a PDF is currently loaded
        if getattr(self, 'pdf_document', None):
            try:
                # render current page to fit new canvas size
                self._render_page()
            except Exception:
                # swallow errors here; _render_page shows its own messagebox on failure
                pass
    
    def _create_fallback_viewer(self):
        """Create fallback viewer when PyMuPDF is not available.
        Opens PDFs with external viewer instead of integrated viewer.
        """
        
        # Footer
        footer_frame = tk.Frame(content_frame, bg="#ffffff")
        footer_frame.pack(side="bottom", fill="x", pady=20)
        
        support_info = tk.Label(
            footer_frame,
            text="Need help? 📧 support@bobosohomail.com | 🌐 www.bitss.one",
            font=("Arial", 10),
            bg="#ffffff",
            fg="#555555"
        )
        support_info.pack()

        # Header
        header_frame = tk.Frame(self, bg="#004d4d")
        header_frame.pack(fill="x", pady=0)
        
        header = tk.Label(
            header_frame, 
            text="❓ Help & User Guide", 
            font=("Arial", 20, "bold"), 
            bg="#004d4d", 
            fg="white"
        )
        header.pack(pady=15)
        
        sub = tk.Label(
            header_frame,
            text="Complete user manual with screenshots",
            font=("Arial", 11),
            bg="#004d4d",
            fg="#cccccc"
        )
        sub.pack(pady=(0, 15))

        # Main content area
        content_frame = tk.Frame(self, bg="#ffffff", relief="ridge", borderwidth=2)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            content_frame,
            text="📚 BITSS VWAR User Manual",
            font=("Arial", 24, "bold"),
            bg="#ffffff",
            fg="#004d4d"
        )
        title_label.pack(pady=30)
        
        # Description
        desc_label = tk.Label(
            content_frame,
            text="Complete guide with step-by-step instructions and screenshots\n"
                 "Available in English and French",
            font=("Arial", 12),
            bg="#ffffff",
            fg="#555555",
            justify="center"
        )
        desc_label.pack(pady=10)
        
        # PDF Buttons Frame
        pdf_frame = tk.Frame(content_frame, bg="#ffffff")
        pdf_frame.pack(pady=40)
        
        # Find PDF files
        english_pdf = self._find_pdf("English")
        french_pdf = self._find_pdf("French")
        
        # English PDF Button
        if english_pdf:
            english_btn = tk.Button(
                pdf_frame,
                text="📄 Open English User Manual",
                command=lambda: self._open_pdf(english_pdf, "English"),
                bg="#007777",
                fg="white",
                font=("Arial", 14, "bold"),
                padx=30,
                pady=15,
                relief="raised",
                cursor="hand2",
                borderwidth=3
            )
            english_btn.pack(pady=10)
            
            # Show file info
            file_size = self._get_file_size(english_pdf)
            tk.Label(
                pdf_frame,
                text=f"File: {os.path.basename(english_pdf)} ({file_size})",
                font=("Arial", 9),
                bg="#ffffff",
                fg="#666666"
            ).pack()
        
        # French PDF Button
        if french_pdf:
            french_btn = tk.Button(
                pdf_frame,
                text="📄 Ouvrir le Manuel Utilisateur Français",
                command=lambda: self._open_pdf(french_pdf, "French"),
                bg="#007777",
                fg="white",
                font=("Arial", 14, "bold"),
                padx=30,
                pady=15,
                relief="raised",
                cursor="hand2",
                borderwidth=3
            )
            french_btn.pack(pady=10)
            
            # Show file info
            file_size = self._get_file_size(french_pdf)
            tk.Label(
                pdf_frame,
                text=f"Fichier: {os.path.basename(french_pdf)} ({file_size})",
                font=("Arial", 9),
                bg="#ffffff",
                fg="#666666"
            ).pack()
        
        # Warning if no PDFs found
        if not english_pdf and not french_pdf:
            tk.Label(
                pdf_frame,
                text="⚠️ User manual PDFs not found\n"
                     "Please contact support: support@bobosohomail.com",
                font=("Arial", 12, "bold"),
                bg="#ffffff",
                fg="#cc0000",
                justify="center"
            ).pack(pady=20)
        
        # Separator
        separator = tk.Frame(content_frame, bg="#cccccc", height=2)
        separator.pack(fill="x", padx=50, pady=30)
        
        # Quick Links Section
        links_title = tk.Label(
            content_frame,
            text="📞 Need More Help?",
            font=("Arial", 16, "bold"),
            bg="#ffffff",
            fg="#004d4d"
        )
        links_title.pack(pady=10)
        
        links_frame = tk.Frame(content_frame, bg="#ffffff")
        links_frame.pack(pady=10)
        
        # Support Info
        support_info = [
            ("🌐 Website:", "http://www.bitss.one"),
            ("📧 Support Email:", "support@bobosohomail.com"),
            ("🏢 Developer:", "Bitss.one"),
        ]
        
        for label_text, value_text in support_info:
            row = tk.Frame(links_frame, bg="#ffffff")
            row.pack(pady=5)
            tk.Label(row, text=label_text, font=("Arial", 11, "bold"),
                    bg="#ffffff", fg="#004d4d").pack(side="left", padx=5)
            tk.Label(row, text=value_text, font=("Arial", 11),
                    bg="#ffffff", fg="#007777").pack(side="left")
        
        # Version info
        version_label = tk.Label(
            content_frame,
            text=f"VWAR Version {self._get_version()}",
            font=("Arial", 10),
            bg="#ffffff",
            fg="#999999"
        )
        version_label.pack(pady=20)

    def _find_pdf(self, language):
        """Find PDF file for specified language (English or French).
        
        Args:
            language: "English" or "French"
            
        Returns:
            Full path to PDF file or None if not found
        """
        # Check in assets folder
        assets_dir = resource_path("assets")
        
        print(f"[HELP] Searching for {language} PDF in: {assets_dir}")
        print(f"[HELP] Assets folder exists: {os.path.exists(assets_dir)}")
        
        # Try to find PDF with language keyword in filename
        try:
            if os.path.exists(assets_dir):
                files = os.listdir(assets_dir)
                print(f"[HELP] Files in assets folder: {files}")
                
                for filename in files:
                    if filename.lower().endswith('.pdf'):
                        print(f"[HELP] Found PDF: {filename}")
                        if language.lower() in filename.lower():
                            full_path = os.path.join(assets_dir, filename)
                            print(f"[HELP] Matched {language} PDF: {full_path}")
                            if os.path.exists(full_path):
                                print(f"[HELP] Returning PDF path: {full_path}")
                                return full_path
            else:
                print(f"[HELP] Assets folder does not exist: {assets_dir}")
        except Exception as e:
            print(f"[HELP] Error searching for {language} PDF: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"[HELP] No {language} PDF found")
        return None
    
    def _open_pdf_external(self, pdf_path, language):
        """Open PDF file with default PDF viewer (fallback method).
        
        Args:
            pdf_path: Full path to PDF file
            language: Language name for display
        """
        try:
            if not os.path.exists(pdf_path):
                messagebox.showerror(
                    "File Not Found",
                    f"The {language} user manual could not be found:\n{pdf_path}"
                )
                return
            
            # Open with default PDF viewer
            os.startfile(pdf_path)
            print(f"[HELP] Opened {language} PDF externally: {pdf_path}")
            
        except Exception as e:
            messagebox.showerror(
                "Error Opening PDF",
                f"Failed to open {language} user manual:\n{str(e)}\n\n"
                f"Please open the file manually:\n{pdf_path}"
            )
            print(f"[HELP] Error opening PDF: {e}")
    
    def _get_file_size(self, file_path):
        """Get human-readable file size.
        
        Args:
            file_path: Full path to file
            
        Returns:
            Formatted size string (e.g., "2.5 MB")
        """
        try:
            size_bytes = os.path.getsize(file_path)
            
            # Convert to appropriate unit
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            
            return f"{size_bytes:.1f} TB"
        except Exception:
            return "Unknown size"
    
    def _get_version(self):
        """Get current VWAR version."""
        try:
            from config import CURRENT_VERSION
            return CURRENT_VERSION
        except Exception:
            return "3.0.0"
