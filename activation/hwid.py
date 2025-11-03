import subprocess


def get_processor_info():
    try:
        result = subprocess.run(
            ['wmic', 'cpu', 'get', 'Name,ProcessorId'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if len(lines) >= 2:
            header = lines[0].split()
            values = lines[1].split()
            # Handle names with spaces
            if len(values) > 2:
                processor_id = values[-1]
                processor_name = ' '.join(values[:-1])
            else:
                processor_name, processor_id = values
            return f"{processor_name} | {processor_id}"
        else:
            return None
    except Exception as e:
        print(f"[ERROR] Failed to get processor info: {e}")
        return None


def get_motherboard_info():
    try:
        result = subprocess.run(
            ['wmic', 'baseboard', 'get', 'Product,Manufacturer,SerialNumber'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if len(lines) >= 2:
            header = lines[0].split()
            values = lines[1].split()

            # Detect serial from the right
            serial = values[-1]
            product = values[-2]
            manufacturer = ' '.join(values[:-2])  # Remaining part is manufacturer (with spaces)

            return f"{manufacturer} {product} | {serial}"
        else:
            return None
    except Exception as e:
        print(f"[ERROR] Failed to get motherboard info: {e}")
        return None
