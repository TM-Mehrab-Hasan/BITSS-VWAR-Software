from tkinter import Frame, Label, Button
from datetime import datetime, timedelta

# Static bullet terms
LICENSE_TERMS = [
    "🔄 Your license auto-renews on the expiration date.",
    "💳 Payment is due within 7 days after renewal.",
    "⚠️ If unpaid, your license will be suspended.",
    "💰 Reactivation Fee: €25 + annual license cost.",
    "❌ Cancel auto-renewal at least 30 days before expiration.",
    "📬 Support: support@bobosohomail.com",
    "🌐 Website: www.bitss.fr"
]

# Status-based messages with {date} placeholder
LICENSE_MESSAGES = {
    "active": "✅ Your license is active. Valid till {date}.",
    "expiring_soon": "⚠️ Your license will expire on {date}. Please renew soon.",
    "renewed_but_unpaid": "⏳ Your license was renewed on {date} but payment is pending.",
    "suspended": "❌ Your license was suspended after {date}. Contact support.",
    "invalid": "⚠️ License data missing or unreadable."
}


class LicenseTermsPage(Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        
        # Store reference to controller for updates
        self.controller = controller
        
        # Create static title
        Label(self, text="📜 VWAR License Terms", font=("Arial", 18, "bold"),
                    bg="white", fg="#333").pack(pady=10)
        
        # Create dynamic labels that will be updated
        self.user_label = Label(self, text="", font=("Arial", 18, "bold"),
                               bg="white", fg="#333")
        self.user_label.pack(pady=10)
        
        self.created_at_label = Label(self, text="", font=("Arial", 18, "bold"),
                                     bg="white", fg="#333")
        self.created_at_label.pack(pady=10)
        
        self.expiry_message_label = Label(self, text="", font=("Arial", 14, "bold"),
                                         bg="white", fg="red")
        self.expiry_message_label.pack(pady=20)
        
        # Days remaining display (large, color-coded)
        self.days_remaining_label = Label(self, text="", font=("Arial", 16, "bold"),
                                         bg="white")
        self.days_remaining_label.pack(pady=10)
        
        # Auto-Renew Status - Dynamic label that updates based on controller's auto_renew_var
        self.auto_renew_status_label = Label(self, text="", font=("Arial", 14, "bold"),
                                             bg="white")
        self.auto_renew_status_label.pack(pady=10)
        
        # Perform initial update
        self.refresh_license_data()
        
        # Start periodic updates (every 2 seconds for real-time sync)
        self._start_periodic_refresh()

        # Back button
        Button(self, text="⬅ Back to Home", font=("Arial", 12),
               command=lambda: controller.show_page("home")).pack(pady=20)
    
    def _start_periodic_refresh(self):
        """Start periodic refresh of license data."""
        def refresh_loop():
            if not self.winfo_exists():
                return  # Stop if widget destroyed
            try:
                self.refresh_license_data()
            except Exception as e:
                print(f"[LICENSE_TERMS] Refresh error: {e}")
            # Schedule next refresh in 2 seconds
            self.after(2000, refresh_loop)
        
        # Start the loop
        refresh_loop()
    
    def refresh_license_data(self):
        """Refresh all dynamic license data from activation file."""
        try:
            from cryptography.fernet import Fernet
            import base64, hashlib, json, os
            from config import ACTIVATION_FILE
            
            # Generate decryption key
            def generate_fernet_key_from_string(secret_string):
                sha256 = hashlib.sha256(secret_string.encode()).digest()
                return base64.urlsafe_b64encode(sha256)
            
            SECRET_KEY = generate_fernet_key_from_string("VWAR@BIFIN")
            fernet = Fernet(SECRET_KEY)
            
            # Read activation file
            with open(ACTIVATION_FILE, "rb") as f:
                encrypted = f.read()
                decrypted = fernet.decrypt(encrypted)
                data = json.loads(decrypted.decode("utf-8"))
            
            activated_user = data.get("username", "Unknown")
            valid_till = data.get("valid_till", "Unknown")
            created_at = data.get("created_at", "Unknown")
            
            # Update labels
            self.user_label.config(text=f"USER : {activated_user}")
            self.created_at_label.config(text=f"Created AT : {created_at}")
            
            # Calculate license status and days remaining
            try:
                # Parse valid_till date
                try:
                    parsed_date = datetime.strptime(valid_till, "%Y-%m-%d %H:%M:%S").date()
                except ValueError:
                    parsed_date = datetime.strptime(valid_till, "%Y-%m-%d").date()
                
                status = self.get_license_status(parsed_date.strftime("%Y-%m-%d"))
                message = LICENSE_MESSAGES.get(status, "").format(
                    date=valid_till if status != "invalid" else "N/A"
                )
                
                # Calculate days remaining
                today = datetime.today().date()
                days_left = (parsed_date - today).days
                
                # Update expiry message
                self.expiry_message_label.config(text=message)
                
                # Update days remaining with color coding
                if days_left > 30:
                    days_color = "green"
                    days_text = f"📅 License Valid for {days_left} Days"
                elif days_left > 15:
                    days_color = "#FFD700"  # Yellow/Gold
                    days_text = f"📅 License Valid for {days_left} Days"
                elif days_left > 7:
                    days_color = "#FF6600"  # Orange
                    days_text = f"⚠️ License Valid for {days_left} Days"
                elif days_left > 0:
                    days_color = "#FF0000"  # Red
                    days_text = f"⚠️ License Expires in {days_left} Days!"
                else:
                    days_color = "#FF0000"  # Red
                    days_text = f"❌ License Expired {abs(days_left)} Days Ago"
                
                self.days_remaining_label.config(text=days_text, fg=days_color)
                
            except Exception as e:
                self.expiry_message_label.config(text="⚠️ License data invalid")
                self.days_remaining_label.config(text="")
            
            # Update auto-renew status
            self.update_auto_renew_display()
            
        except Exception as e:
            print(f"[LICENSE_TERMS] Failed to refresh license data: {e}")
            self.user_label.config(text="USER : Unknown")
            self.created_at_label.config(text="Created AT : Unknown")
            self.expiry_message_label.config(text="⚠️ Failed to load license data")
            self.days_remaining_label.config(text="")
    
    def update_auto_renew_display(self):
        """Update the auto-renew status display based on controller's current value."""
        try:
            # Get current value from controller's auto_renew_var
            if hasattr(self.controller, 'auto_renew_var'):
                current_value = self.controller.auto_renew_var.get()
                auto_renew_enabled = (current_value == "YES")
            else:
                # Fallback to fetching from database if controller doesn't have the var
                from activation.license_utils import get_auto_renew_status
                auto_renew_enabled = get_auto_renew_status()
            
            auto_renew_text = "✅ Auto-Renew: Enabled" if auto_renew_enabled else "❌ Auto-Renew: Disabled"
            auto_renew_color = "green" if auto_renew_enabled else "red"
            
            self.auto_renew_status_label.config(text=auto_renew_text, fg=auto_renew_color)
            
        except Exception as e:
            # Silent fail
            pass

    def get_license_status(self, valid_till_str):
        today = datetime.today().date()
        try:
            expiry = datetime.strptime(valid_till_str, "%Y-%m-%d").date()
        except Exception:
            return "invalid"

        if today > expiry + timedelta(days=7):
            return "suspended"
        elif today > expiry:
            return "renewed_but_unpaid"
        elif expiry - today <= timedelta(days=7):
            return "expiring_soon"
        else:
            return "active"
