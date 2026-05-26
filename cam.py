import subprocess

def enable_camera():
    try:
        # Run PowerShell command to enable the camera
        command = 'Get-PnpDevice -Class Image | Enable-PnpDevice -Confirm:$false'
        subprocess.run(["powershell", "-Command", command], shell=True, check=True)
        print("✅ Camera has been enabled successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    enable_camera()
