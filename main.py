#!/usr/bin/env python3
"""
SMB Server Setup Script for Anonymous Access
Sets up Samba server to share /srv/shared directory
with anonymous access for Windows Guest OS connection.
"""

import os
import sys
import subprocess
import shutil
import time
import select
import datetime

# Global configuration variables
NETWORK_PATH = "/srv/shared"


class SMBServerSetup:
    def __init__(self, share_path=None, debug_mode=False):
        self.share_path = share_path or NETWORK_PATH
        self.share_name = "shared"
        self.samba_config = "/etc/samba/smb.conf"
        self.backup_config = "/etc/samba/smb.conf.backup"
        self.bind_interfaces = None  # Will be set during interface selection
        self.bind_interface_name = None  # Interface name for Samba config
        self.debug_mode = debug_mode
        self.smb_min_protocol = "NT1"  # Default to SMBv1 for compatibility
        self.smb_max_protocol = "SMB3"  # Support up to SMB3

    def check_root_privileges(self):
        """Check if script is running with root privileges"""
        if os.geteuid() != 0:
            print("❌ This script requires root privileges to configure Samba.")
            print("Please run with: sudo python3 main.py")
            sys.exit(1)
        print("✅ Running with root privileges")

    def check_share_directory(self):
        """Check if share directory exists and create if needed"""
        if not os.path.exists(self.share_path):
            print(f"📁 Creating share directory: {self.share_path}")
            try:
                os.makedirs(self.share_path, mode=0o755, exist_ok=True)
                print(f"✅ Directory created: {self.share_path}")
            except Exception as e:
                print(f"❌ Failed to create directory: {e}")
                sys.exit(1)
        else:
            print(f"✅ Share directory exists: {self.share_path}")
    
    def get_network_interfaces(self):
        """Get available network interfaces with their IP addresses"""
        interfaces = []
        
        try:
            # Use ip command to get interface information
            result = subprocess.run(["ip", "-4", "addr", "show"], 
                                  capture_output=True, text=True, check=True)
            
            current_interface = None
            for line in result.stdout.split('\n'):
                line = line.strip()
                
                # Look for interface lines (start with number)
                if line and line[0].isdigit() and ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        current_interface = parts[1].strip()
                
                # Look for IP addresses
                elif line.startswith('inet ') and current_interface:
                    inet_parts = line.split()
                    if len(inet_parts) >= 2:
                        ip_cidr = inet_parts[1]
                        ip_addr = ip_cidr.split('/')[0]
                        
                        # Skip loopback
                        if not ip_addr.startswith('127.'):
                            interfaces.append({
                                'name': current_interface,
                                'ip': ip_addr,
                                'cidr': ip_cidr
                            })
            
        except subprocess.CalledProcessError:
            # Fallback: try using hostname command
            try:
                result = subprocess.run(["hostname", "-I"], 
                                      capture_output=True, text=True, check=True)
                ips = result.stdout.strip().split()
                for i, ip in enumerate(ips):
                    if not ip.startswith('127.'):
                        interfaces.append({
                            'name': f'interface{i+1}',
                            'ip': ip,
                            'cidr': f'{ip}/24'
                        })
            except subprocess.CalledProcessError:
                pass
        
        return interfaces
    
    def get_user_input_with_timeout(self, prompt, timeout=60):
        """Get user input with timeout"""
        print(prompt, end='', flush=True)
        
        # For Unix-like systems
        if hasattr(select, 'select'):
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if ready:
                return sys.stdin.readline().strip()
            else:
                return None
        else:
            # Fallback for systems without select
            print(f"\nAuto-selecting default option in {timeout} seconds...")
            time.sleep(timeout)
            return None
    
    def select_network_binding(self):
        """Let user select network interface binding with countdown"""
        print("\n🌐 Network Interface Detection")
        print("="*50)
        
        interfaces = self.get_network_interfaces()
        
        if not interfaces:
            print("❌ No network interfaces detected. Cannot proceed with Samba setup.")
            print("💡 Please ensure your network interfaces are properly configured.")
            sys.exit(1)
        
        print("📡 Available network interfaces:")
        print()
        
        options = []
        
        # Add detected interfaces (no default 0.0.0.0 option)
        for i, interface in enumerate(interfaces, 1):
            options.append({
                'key': str(i),
                'description': f"Bind to {interface['name']} ({interface['ip']})",
                'value': interface['ip']
            })
        
        # Display options
        for option in options:
            print(f"  [{option['key']}] {option['description']}")
        
        print()
        print("🕐 You have 60 seconds to choose an option.")
        print("⏰ If no input is provided, the first available interface will be selected automatically.")
        print()
        
        # Countdown with user input
        user_input = None
        for remaining in range(60, 0, -1):
            prompt = f"⌛ Select option [1-{len(options)}] ({remaining}s remaining): "
            
            try:
                # Use select for non-blocking input with 1-second timeout
                if hasattr(select, 'select'):
                    print(f"\r{prompt}", end='', flush=True)
                    ready, _, _ = select.select([sys.stdin], [], [], 1)
                    if ready:
                        user_input = sys.stdin.readline().strip()
                        if user_input:
                            break
                else:
                    # Fallback for systems without select
                    if remaining == 60:
                        print(prompt, end='', flush=True)
                    time.sleep(1)
                    continue
            except (KeyboardInterrupt, EOFError):
                print("\n\n❌ Selection interrupted, using first available interface")
                user_input = "1"
                break
        else:
            # Timeout reached
            print("\r⏰ Timeout reached! Auto-selecting first available interface...")
            user_input = "1"
        
        # Process user input
        try:
            choice_index = int(user_input) - 1  # Convert to 0-based index
            if 0 <= choice_index < len(options):
                selected_option = options[choice_index]
                self.bind_interfaces = selected_option['value']
                # Also store the interface name for Samba config
                interfaces_data = self.get_network_interfaces()
                for interface in interfaces_data:
                    if interface['ip'] == selected_option['value']:
                        self.bind_interface_name = interface['name']
                        break
                # Fallback if interface name not found
                if not self.bind_interface_name:
                    self.bind_interface_name = "eth0"  # Common default
                print(f"\n✅ Selected: {selected_option['description']}")
            else:
                print(f"\n⚠️  Invalid choice '{user_input}', using first available interface")
                selected_option = options[0]
                self.bind_interfaces = selected_option['value']
                # Also store the interface name for Samba config
                interfaces_data = self.get_network_interfaces()
                for interface in interfaces_data:
                    if interface['ip'] == selected_option['value']:
                        self.bind_interface_name = interface['name']
                        break
                # Fallback if interface name not found
                if not self.bind_interface_name:
                    self.bind_interface_name = "eth0"  # Common default
                print(f"✅ Auto-selected: {selected_option['description']}")
        except (ValueError, IndexError):
            print(f"\n⚠️  Invalid input '{user_input}', using first available interface")
            selected_option = options[0]
            self.bind_interfaces = selected_option['value']
            # Also store the interface name for Samba config
            interfaces_data = self.get_network_interfaces()
            for interface in interfaces_data:
                if interface['ip'] == selected_option['value']:
                    self.bind_interface_name = interface['name']
                    break
            # Fallback if interface name not found
            if not self.bind_interface_name:
                self.bind_interface_name = "eth0"  # Common default
            print(f"✅ Auto-selected: {selected_option['description']}")
        
        print(f"🔗 Samba will bind to: {self.bind_interface_name} ({self.bind_interfaces})")
        print()

    def select_smb_version(self):
        """Allow user to select SMB protocol version with timeout"""
        print("\n📡 SMB Protocol Version Selection")
        print("=" * 50)
        
        # Define SMB version options
        smb_options = [
            {
                'name': 'SMBv1 (NT1)',
                'min_protocol': 'NT1',
                'max_protocol': 'SMB3',
                'description': 'SMBv1 to SMBv3 - Maximum compatibility (includes legacy Windows)',
                'compatibility': 'Best for: Windows XP, older systems, maximum compatibility',
                'security': '⚠️  Less secure but most compatible'
            },
            {
                'name': 'SMBv2',
                'min_protocol': 'SMB2',
                'max_protocol': 'SMB3',
                'description': 'SMBv2 to SMBv3 - Good balance of security and compatibility',
                'compatibility': 'Best for: Windows 7+, modern systems',
                'security': '✅ More secure than SMBv1'
            },
            {
                'name': 'SMBv3 Only',
                'min_protocol': 'SMB3',
                'max_protocol': 'SMB3',
                'description': 'SMBv3 only - Maximum security',
                'compatibility': 'Best for: Windows 8+, latest systems only',
                'security': '🔒 Most secure, requires modern clients'
            }
        ]
        
        # Display options
        for i, option in enumerate(smb_options):
            print(f"\n  [{i}] {option['name']}")
            print(f"      {option['description']}")
            print(f"      {option['compatibility']}")
            print(f"      {option['security']}")
        
        print("\n🕐 You have 60 seconds to choose an option.")
        print("⏰ If no input is provided, option [0] (SMBv1 compatibility) will be selected automatically.")
        print("💡 SMBv1 is recommended for maximum compatibility with older Windows systems.")
        
        # Timeout selection logic
        user_input = None
        start_time = time.time()
        timeout = 60
        
        while time.time() - start_time < timeout:
            remaining = int(timeout - (time.time() - start_time))
            prompt = f"\n⌛ Select option [0-{len(smb_options)-1}] ({remaining}s remaining): "
            
            try:
                # Check if input is available
                sys.stdout.write(f"\r{prompt}")
                sys.stdout.flush()
                
                # Use select to check for input availability (Unix-like systems)
                if hasattr(select, 'select'):
                    ready, _, _ = select.select([sys.stdin], [], [], 1)
                    if ready:
                        user_input = sys.stdin.readline().strip()
                        break
                else:
                    # Fallback for systems without select
                    if remaining == 60:
                        print(prompt, end='', flush=True)
                    time.sleep(1)
                    continue
            except (KeyboardInterrupt, EOFError):
                print("\n\n❌ Selection interrupted, using default SMBv1 compatibility")
                user_input = "0"
                break
        else:
            # Timeout reached
            print("\r⏰ Timeout reached! Auto-selecting option [0] (SMBv1 compatibility)...")
            user_input = "0"
        
        # Process user input
        try:
            choice_index = int(user_input) if user_input else 0
            if 0 <= choice_index < len(smb_options):
                selected_option = smb_options[choice_index]
                self.smb_min_protocol = selected_option['min_protocol']
                self.smb_max_protocol = selected_option['max_protocol']
                print(f"\n✅ Selected: {selected_option['name']}")
                print(f"    Min Protocol: {self.smb_min_protocol}")
                print(f"    Max Protocol: {self.smb_max_protocol}")
                print(f"    {selected_option['security']}")
            else:
                print(f"\n⚠️  Invalid choice '{user_input}', using default SMBv1 compatibility")
                self.smb_min_protocol = "NT1"
                self.smb_max_protocol = "SMB3"
        except ValueError:
            print(f"\n⚠️  Invalid input '{user_input}', using default SMBv1 compatibility")
            self.smb_min_protocol = "NT1"
            self.smb_max_protocol = "SMB3"
        
        print(f"🔐 SMB Protocol Configuration: {self.smb_min_protocol} to {self.smb_max_protocol}")
        print()

    def detect_os(self):
        """Detect the operating system and return package manager info"""
        print("🔍 Detecting operating system...")

        try:
            # Check for Debian/Ubuntu systems
            if os.path.exists("/etc/debian_version"):
                print("✅ Detected Debian-based system (Ubuntu/Debian)")
                return {
                    "type": "debian",
                    "update_cmd": ["apt", "update"],
                    "install_cmd": ["apt", "install", "-y", "samba"],
                    "package_manager": "apt"
                }

            # Check for Red Hat/Fedora systems
            elif os.path.exists("/etc/redhat-release") or os.path.exists("/etc/fedora-release"):
                print("✅ Detected Red Hat-based system (Fedora/RHEL/CentOS)")
                return {
                    "type": "redhat",
                    "update_cmd": ["dnf", "check-update"],
                    "install_cmd": ["dnf", "install", "-y", "samba"],
                    "package_manager": "dnf"
                }

            # Check for older CentOS/RHEL systems that might use yum
            elif os.path.exists("/etc/centos-release"):
                # Check if dnf is available, fallback to yum
                try:
                    subprocess.run(["which", "dnf"], check=True,
                                   capture_output=True)
                    print("✅ Detected CentOS with DNF")
                    return {
                        "type": "redhat",
                        "update_cmd": ["dnf", "check-update"],
                        "install_cmd": ["dnf", "install", "-y", "samba"],
                        "package_manager": "dnf"
                    }
                except subprocess.CalledProcessError:
                    print("✅ Detected CentOS with YUM")
                    return {
                        "type": "redhat",
                        "update_cmd": ["yum", "check-update"],
                        "install_cmd": ["yum", "install", "-y", "samba"],
                        "package_manager": "yum"
                    }

            # Check for Arch Linux
            elif os.path.exists("/etc/arch-release"):
                print("✅ Detected Arch Linux")
                return {
                    "type": "arch",
                    "update_cmd": ["pacman", "-Sy"],
                    "install_cmd": ["pacman", "-S", "--noconfirm", "samba"],
                    "package_manager": "pacman"
                }

            # Check for openSUSE
            elif os.path.exists("/etc/SUSE-brand") or os.path.exists("/etc/SuSE-release"):
                print("✅ Detected openSUSE")
                return {
                    "type": "suse",
                    "update_cmd": ["zypper", "refresh"],
                    "install_cmd": ["zypper", "install", "-y", "samba"],
                    "package_manager": "zypper"
                }

            else:
                # Default to apt for unknown systems
                print("⚠️  Unknown Linux distribution, defaulting to apt")
                return {
                    "type": "unknown",
                    "update_cmd": ["apt", "update"],
                    "install_cmd": ["apt", "install", "-y", "samba"],
                    "package_manager": "apt"
                }

        except Exception as e:
            print(f"⚠️  Error detecting OS: {e}, defaulting to apt")
            return {
                "type": "unknown",
                "update_cmd": ["apt", "update"],
                "install_cmd": ["apt", "install", "-y", "samba"],
                "package_manager": "apt"
            }

    def install_samba(self):
        """Install Samba server if not already installed"""
        print("🔍 Checking if Samba is installed...")

        # Check if samba is installed
        try:
            subprocess.run(["which", "smbd"], check=True, capture_output=True)
            print("✅ Samba is already installed")
            return
        except subprocess.CalledProcessError:
            pass

        # Detect OS and get package manager info
        os_info = self.detect_os()

        print(
            f"📦 Installing Samba server using {os_info['package_manager']}...")
        try:
            # Update package list (skip for dnf check-update as it may return non-zero)
            if os_info['type'] == 'redhat' and 'check-update' in os_info['update_cmd']:
                print(
                    f"🔄 Checking for updates with {os_info['package_manager']}...")
                # dnf check-update returns exit code 100 when updates are available
                result = subprocess.run(
                    os_info['update_cmd'], capture_output=True)
                if result.returncode not in [0, 100]:
                    print(
                        f"⚠️  Update check returned code {result.returncode}, continuing...")
            else:
                print(
                    f"🔄 Updating package list with {os_info['package_manager']}...")
                subprocess.run(os_info['update_cmd'], check=True)

            # Install samba
            print(f"📥 Installing Samba with {os_info['package_manager']}...")
            subprocess.run(os_info['install_cmd'], check=True)
            print("✅ Samba installed successfully")
        except subprocess.CalledProcessError as e:
            print(
                f"❌ Failed to install Samba with {os_info['package_manager']}: {e}")
            print(f"💡 Try manually: sudo {' '.join(os_info['install_cmd'])}")
            sys.exit(1)

    def backup_samba_config(self):
        """Backup existing Samba configuration"""
        if os.path.exists(self.samba_config):
            if not os.path.exists(self.backup_config):
                print("💾 Backing up existing Samba configuration...")
                try:
                    shutil.copy2(self.samba_config, self.backup_config)
                    print(f"✅ Backup created: {self.backup_config}")
                except Exception as e:
                    print(f"❌ Failed to backup config: {e}")
                    sys.exit(1)
            else:
                print("✅ Backup already exists")

    def create_samba_config(self):
        """Create Samba configuration for anonymous access"""
        print("⚙️  Creating Samba configuration...")

        # Get appropriate nobody user and group for this system
        nobody_user, nobody_group = self.get_nobody_user_group()

        config_content = f"""# Samba configuration for anonymous access
# Global settings
[global]
    workgroup = WORKGROUP
    server string = SMB Server for File Sharing
    netbios name = SMBSERVER
    security = user
    map to guest = bad user
    guest account = {nobody_user}
    
    # Network binding
    interfaces = {self.bind_interface_name}
    bind interfaces only = yes
    
    # Disable printing
    load printers = no
    printing = bsd
    printcap name = /dev/null
    disable spoolss = yes
    
    # Performance and compatibility
    socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=65536 SO_SNDBUF=65536
    min protocol = {self.smb_min_protocol}
    max protocol = {self.smb_max_protocol}
    
    # Logging
    log file = /var/log/samba/log.%m
    max log size = 1000
    log level = 1

# Anonymous share for shared directory
[{self.share_name}]
    comment = Shared Directory (Anonymous Access)
    path = {self.share_path}
    browseable = yes
    writable = yes
    guest ok = yes
    guest only = yes
    create mask = 0755
    directory mask = 0755
    force user = {nobody_user}
    force group = {nobody_group}
    public = yes
"""

        try:
            with open(self.samba_config, 'w') as f:
                f.write(config_content)
            print(f"✅ Samba configuration created: {self.samba_config}")
        except Exception as e:
            print(f"❌ Failed to create config: {e}")
            sys.exit(1)

    def get_nobody_user_group(self):
        """Get the appropriate nobody user and group for the current system"""
        print("🔍 Detecting nobody user and group...")

        # Common combinations to try
        combinations = [
            ("nobody", "nobody"),      # Most common on Red Hat systems
            ("nobody", "nogroup"),     # Common on Debian systems
            ("nobody", "wheel"),       # Some systems
            ("nfsnobody", "nfsnobody")  # Some Red Hat systems
        ]

        for user, group in combinations:
            try:
                # Check if user exists
                subprocess.run(["id", user], check=True, capture_output=True)
                # Check if group exists
                subprocess.run(["getent", "group", group],
                               check=True, capture_output=True)
                print(f"✅ Found nobody user/group: {user}:{group}")
                return user, group
            except subprocess.CalledProcessError:
                continue

        # If none found, create a fallback approach
        print("⚠️  Standard nobody user/group not found, using current user")
        try:
            # Get current user
            current_user = os.getenv(
                'SUDO_USER') or os.getenv('USER') or 'root'
            # Try to get primary group
            result = subprocess.run(["id", "-gn", current_user],
                                    capture_output=True, text=True, check=True)
            current_group = result.stdout.strip()
            print(f"📝 Using fallback: {current_user}:{current_group}")
            return current_user, current_group
        except Exception:
            # Ultimate fallback
            print("📝 Using ultimate fallback: root:root")
            return "root", "root"

    def set_directory_permissions(self):
        """Set proper permissions for the shared directory"""
        print("🔐 Setting directory permissions...")
        try:
            # Make directory accessible to everyone
            os.chmod(self.share_path, 0o755)

            # Get appropriate nobody user and group for this system
            nobody_user, nobody_group = self.get_nobody_user_group()

            # Change ownership for anonymous access
            chown_command = ["chown", "-R",
                             f"{nobody_user}:{nobody_group}", self.share_path]
            subprocess.run(chown_command, check=True)
            print(
                f"✅ Permissions set for {self.share_path} (owner: {nobody_user}:{nobody_group})")
        except Exception as e:
            print(f"❌ Failed to set permissions: {e}")
            print("🔧 Attempting alternative permission setup...")
            try:
                # Alternative: just make it world-readable/writable
                os.chmod(self.share_path, 0o777)
                print(
                    f"✅ Set alternative permissions (777) for {self.share_path}")
                print(
                    "⚠️  Note: Directory is world-writable. Consider security implications.")
            except Exception as e2:
                print(f"❌ Failed alternative permission setup: {e2}")
                print("💡 You may need to manually set permissions after setup completes")
                print(f"💡 Try: sudo chmod 755 {self.share_path}")
                # Don't exit here, continue with setup

    def get_samba_service_names(self):
        """Get the correct Samba service names for the current distribution"""
        print("🔍 Detecting Samba service names...")

        # Common service name combinations to try
        service_combinations = [
            # Red Hat/Fedora/CentOS modern
            {"smb": "smb", "nmb": "nmb"},
            {"smb": "smbd", "nmb": "nmbd"},         # Debian/Ubuntu
            {"smb": "samba", "nmb": "nmb"},         # Some systems
            {"smb": "samba", "nmb": "winbind"},     # Alternative
        ]

        for services in service_combinations:
            smb_service = services["smb"]
            nmb_service = services["nmb"]

            try:
                # Check if the smb service exists
                result = subprocess.run(["systemctl", "list-unit-files", f"{smb_service}.service"],
                                        capture_output=True, text=True)
                if f"{smb_service}.service" in result.stdout:
                    print(
                        f"✅ Found Samba services: {smb_service}, {nmb_service}")
                    return smb_service, nmb_service
            except subprocess.CalledProcessError:
                continue

        # If no services found with systemctl, try alternative detection
        print("🔍 Trying alternative service detection...")

        # Check what's actually installed
        try:
            result = subprocess.run(["systemctl", "list-unit-files", "*smb*", "*samba*"],
                                    capture_output=True, text=True)
            if "smb.service" in result.stdout:
                print("✅ Found services: smb, nmb")
                return "smb", "nmb"
            elif "smbd.service" in result.stdout:
                print("✅ Found services: smbd, nmbd")
                return "smbd", "nmbd"
            elif "samba.service" in result.stdout:
                print("✅ Found service: samba")
                return "samba", None  # Some systems only have samba service
        except subprocess.CalledProcessError:
            pass

        # Default fallback
        print("⚠️  Using default service names: smbd, nmbd")
        return "smbd", "nmbd"

    def start_samba_services(self):
        """Start and enable Samba services"""
        print("🚀 Starting Samba services...")

        # Get correct service names for this distribution
        smb_service, nmb_service = self.get_samba_service_names()

        services_started = []
        services_failed = []

        # Try to start SMB service
        try:
            print(f"🔧 Enabling {smb_service} service...")
            subprocess.run(["systemctl", "enable", smb_service], check=True)
            print(f"🚀 Starting {smb_service} service...")
            subprocess.run(["systemctl", "start", smb_service], check=True)
            services_started.append(smb_service)
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to start {smb_service}: {e}")
            services_failed.append(smb_service)

        # Try to start NMB service (if it exists)
        if nmb_service:
            try:
                print(f"🔧 Enabling {nmb_service} service...")
                subprocess.run(
                    ["systemctl", "enable", nmb_service], check=True)
                print(f"🚀 Starting {nmb_service} service...")
                subprocess.run(["systemctl", "start", nmb_service], check=True)
                services_started.append(nmb_service)
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Failed to start {nmb_service}: {e}")
                services_failed.append(nmb_service)

        # Report results
        if services_started:
            print(
                f"✅ Successfully started services: {', '.join(services_started)}")

        if services_failed:
            print(
                f"⚠️  Failed to start services: {', '.join(services_failed)}")
            print("🔧 Attempting manual service management...")

            # Try alternative approaches
            for service in services_failed:
                try:
                    print(f"🔄 Trying to restart {service}...")
                    subprocess.run(
                        ["systemctl", "restart", service], check=True)
                    print(f"✅ Successfully restarted {service}")
                    services_started.append(service)
                except subprocess.CalledProcessError:
                    print(
                        f"💡 Manual command needed: sudo systemctl start {service}")

        # Check if at least the main SMB service is running
        try:
            result = subprocess.run(["systemctl", "is-active", smb_service],
                                    capture_output=True, text=True)
            if "active" in result.stdout:
                print(f"✅ {smb_service} service is running")
            else:
                print(
                    f"⚠️  {smb_service} service status: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            print(f"⚠️  Could not check {smb_service} service status")

        # Don't exit on service failures, as SMB might still work
        if not services_started:
            print("⚠️  No services were started successfully")
            print("💡 You may need to start services manually after setup:")
            print(f"💡   sudo systemctl start {smb_service}")
            if nmb_service:
                print(f"💡   sudo systemctl start {nmb_service}")
        else:
            print("🎉 Samba service setup completed")

    def test_configuration(self):
        """Test Samba configuration"""
        print("🧪 Testing Samba configuration...")
        try:
            subprocess.run(["testparm", "-s"],
                           capture_output=True, text=True, check=True)
            print("✅ Samba configuration is valid")
        except subprocess.CalledProcessError as e:
            print(f"❌ Configuration test failed: {e}")
            print("Please check the configuration manually")
    
    def configure_firewall(self):
        """Configure firewall to allow Samba traffic"""
        print("🔥 Configuring firewall for Samba...")
        
        # Detect OS to determine firewall approach
        os_info = self.detect_os()
        
        # Skip firewalld check on Debian-based systems as they don't use firewalld by default
        if os_info["type"] == "debian":
            print("ℹ️  Debian-based system detected, skipping firewalld check")
        else:
            # Check if firewalld is available and running (for Red Hat-based systems)
            try:
                result = subprocess.run(["systemctl", "is-active", "firewalld"], 
                                      capture_output=True, text=True)
                if "active" in result.stdout:
                    print("🔍 Detected firewalld, configuring...")
                    # Check if firewall-cmd is available by trying a harmless command
                    try:
                        subprocess.run(["firewall-cmd", "--version"], check=True, capture_output=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        print("⚠️  firewalld detected but firewall-cmd not available, skipping firewalld configuration")
                        pass  # Skip to next firewall
                    else:
                        try:
                            # Add Samba service to default zone permanently
                            subprocess.run(["firewall-cmd", "--add-service=samba", "--permanent"], check=True)
                            subprocess.run(["firewall-cmd", "--add-service=samba"], check=True)
                            
                            # Check if network interface is in libvirt zone and configure accordingly
                            network_interfaces = self.get_network_interfaces()
                            for interface in network_interfaces:
                                if interface['name'].startswith(('virbr', 'libvirt')):
                                    try:
                                        # Check zone of virtual interface
                                        zone_result = subprocess.run(["firewall-cmd", f"--get-zone-of-interface={interface['name']}"], 
                                                                    capture_output=True, text=True, check=True)
                                        zone = zone_result.stdout.strip()
                                        
                                        if zone == "libvirt":
                                            print(f"🔍 Found {interface['name']} in libvirt zone, adding Samba...")
                                            # Add Samba to libvirt zone
                                            subprocess.run(["firewall-cmd", "--zone=libvirt", "--add-service=samba", "--permanent"], check=True)
                                            subprocess.run(["firewall-cmd", "--zone=libvirt", "--add-service=samba"], check=True)
                                            # Add explicit ports as backup
                                            subprocess.run(["firewall-cmd", "--zone=libvirt", "--add-port=445/tcp", "--permanent"], check=True)
                                            subprocess.run(["firewall-cmd", "--zone=libvirt", "--add-port=139/tcp", "--permanent"], check=True)
                                            subprocess.run(["firewall-cmd", "--zone=libvirt", "--add-port=445/tcp"], check=True)
                                            subprocess.run(["firewall-cmd", "--zone=libvirt", "--add-port=139/tcp"], check=True)
                                            print(f"✅ Added Samba to libvirt zone for {interface['name']}")
                                    except subprocess.CalledProcessError:
                                        # Interface might not be assigned to a zone yet
                                        pass
                            
                            # Reload firewall
                            subprocess.run(["firewall-cmd", "--reload"], check=True)
                            print("✅ Firewall configured for Samba (including virtual networks)")
                            return True
                        except subprocess.CalledProcessError as e:
                            print(f"⚠️  Failed to configure firewalld: {e}")
            except subprocess.CalledProcessError:
                pass
        
        # Check if ufw is available
        try:
            subprocess.run(["which", "ufw"], check=True, capture_output=True)
            print("🔍 Detected UFW, configuring...")
            try:
                subprocess.run(["ufw", "allow", "samba"], check=True)
                print("✅ UFW configured for Samba")
                return True
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Failed to configure UFW: {e}")
        except subprocess.CalledProcessError:
            pass
        
        # Check if iptables is available
        try:
            subprocess.run(["which", "iptables"], check=True, capture_output=True)
            print("🔍 Detected iptables, adding rules...")
            try:
                # Add rules for SMB ports
                subprocess.run(["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "445", "-j", "ACCEPT"], check=True)
                subprocess.run(["iptables", "-A", "INPUT", "-p", "tcp", "--dport", "139", "-j", "ACCEPT"], check=True)
                subprocess.run(["iptables", "-A", "INPUT", "-p", "udp", "--dport", "137", "-j", "ACCEPT"], check=True)
                subprocess.run(["iptables", "-A", "INPUT", "-p", "udp", "--dport", "138", "-j", "ACCEPT"], check=True)
                print("✅ iptables configured for Samba")
                print("⚠️  Note: iptables rules are not persistent. Consider saving them.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Failed to configure iptables: {e}")
        except subprocess.CalledProcessError:
            pass
        
        print("ℹ️  No supported firewall detected or firewall configuration failed")
        print("💡 If you have a firewall, manually allow ports 445, 139, 137, 138")
        return False
    
    def check_firewall_status(self):
        """Check and display firewall status for SMB services"""
        print("\n🔥 Checking firewall configuration for SMB...")
        
        try:
            result = subprocess.run(["systemctl", "is-active", "firewalld"], 
                                  capture_output=True, text=True)
            if "active" in result.stdout:
                print("🔍 Firewalld Status:")
                
                # Check default zone
                try:
                    result = subprocess.run(["firewall-cmd", "--list-services"], 
                                          capture_output=True, text=True, check=True)
                    services = result.stdout.strip()
                    if "samba" in services:
                        print("  ✅ Samba service enabled in default zone")
                    else:
                        print("  ❌ Samba service NOT enabled in default zone")
                except subprocess.CalledProcessError:
                    pass
                
                # Check libvirt zone
                try:
                    result = subprocess.run(["firewall-cmd", "--zone=libvirt", "--list-services"], 
                                          capture_output=True, text=True, check=True)
                    services = result.stdout.strip()
                    if "samba" in services:
                        print("  ✅ Samba service enabled in libvirt zone")
                    else:
                        print("  ❌ Samba service NOT enabled in libvirt zone")
                        print("  💡 Run: sudo firewall-cmd --zone=libvirt --add-service=samba --permanent")
                except subprocess.CalledProcessError:
                    print("  ℹ️  Libvirt zone not found")
                
                # Check for explicit ports
                try:
                    result = subprocess.run(["firewall-cmd", "--zone=libvirt", "--list-ports"], 
                                          capture_output=True, text=True, check=True)
                    ports = result.stdout.strip()
                    if "445/tcp" in ports and "139/tcp" in ports:
                        print("  ✅ SMB ports 445/tcp and 139/tcp enabled in libvirt zone")
                    else:
                        print("  ⚠️  SMB ports may not be explicitly enabled in libvirt zone")
                except subprocess.CalledProcessError:
                    pass
                
                return True
        except subprocess.CalledProcessError:
            pass
        
        print("ℹ️  Firewalld not active or not found")
        return False
    
    def configure_selinux(self):
        """Configure SELinux for Samba if available"""
        print("🛡️  Configuring SELinux for Samba...")
        
        try:
            # Check if SELinux is available
            result = subprocess.run(["getenforce"], capture_output=True, text=True, check=True)
            selinux_status = result.stdout.strip()
            
            if selinux_status == "Disabled":
                print("ℹ️  SELinux is disabled, skipping configuration")
                return True
            elif selinux_status in ["Enforcing", "Permissive"]:
                print(f"🔍 SELinux is {selinux_status}, configuring...")
                
                try:
                    # Set SELinux context for the shared directory
                    subprocess.run(["semanage", "fcontext", "-a", "-t", "samba_share_t", 
                                  f"{self.share_path}(/.*)?"], check=True)
                    subprocess.run(["restorecon", "-R", self.share_path], check=True)
                    print(f"✅ SELinux context set for {self.share_path}")
                    
                    # Enable Samba home directory access if needed
                    if "/home/" in self.share_path:
                        subprocess.run(["setsebool", "-P", "samba_enable_home_dirs", "on"], check=True)
                        print("✅ SELinux configured for home directory access")
                    
                    return True
                except subprocess.CalledProcessError as e:
                    print(f"⚠️  Failed to configure SELinux: {e}")
                    print("💡 You may need to manually set SELinux contexts")
                    return False
            else:
                print(f"⚠️  Unknown SELinux status: {selinux_status}")
                return False
                
        except subprocess.CalledProcessError:
            print("ℹ️  SELinux not available, skipping configuration")
            return True
        except FileNotFoundError:
            print("ℹ️  SELinux commands not found, skipping configuration")
            return True
    
    def verify_smb_connectivity(self):
        """Verify SMB server is accessible"""
        print("🔍 Verifying SMB connectivity...")
        
        # Install smbclient if not available
        try:
            subprocess.run(["which", "smbclient"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("📦 Installing samba-client for testing...")
            os_info = self.detect_os()
            try:
                if os_info['type'] == 'redhat':
                    subprocess.run(["dnf", "install", "-y", "samba-client"], check=True)
                else:
                    subprocess.run(["apt", "install", "-y", "smbclient"], check=True)
            except subprocess.CalledProcessError:
                print("⚠️  Could not install smbclient for testing")
                return False
        
        # Test connection
        test_ip = self.bind_interfaces
        
        try:
            print(f"🧪 Testing connection to {test_ip}...")
            result = subprocess.run(["smbclient", "-L", test_ip, "-N"], 
                                  capture_output=True, text=True, check=True)
            
            if self.share_name in result.stdout:
                print(f"✅ SMB server is accessible and {self.share_name} share is visible")
                return True
            else:
                print(f"⚠️  SMB server accessible but {self.share_name} share not found")
                print("Output:", result.stdout)
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ SMB connectivity test failed: {e}")
            return False
    
    def troubleshoot_connectivity(self):
        """Run comprehensive troubleshooting for connectivity issues"""
        print("\n🔧 Running connectivity troubleshooting...")
        print("="*50)
        
        issues_found = []
        fixes_applied = []
        
        # Check if services are running
        smb_service, nmb_service = self.get_samba_service_names()
        
        try:
            result = subprocess.run(["systemctl", "is-active", smb_service], 
                                  capture_output=True, text=True)
            if "active" not in result.stdout:
                issues_found.append(f"{smb_service} service not running")
                try:
                    subprocess.run(["systemctl", "restart", smb_service], check=True)
                    fixes_applied.append(f"Restarted {smb_service} service")
                except subprocess.CalledProcessError:
                    issues_found.append(f"Failed to restart {smb_service}")
        except subprocess.CalledProcessError:
            issues_found.append(f"Cannot check {smb_service} status")
        
        # Configure firewall
        if not self.configure_firewall():
            issues_found.append("Firewall may be blocking SMB traffic")
        else:
            fixes_applied.append("Configured firewall for Samba")
        
        # Configure SELinux
        if not self.configure_selinux():
            issues_found.append("SELinux may be blocking Samba")
        else:
            fixes_applied.append("Configured SELinux for Samba")
        
        # Test connectivity
        if self.verify_smb_connectivity():
            fixes_applied.append("SMB connectivity verified")
        else:
            issues_found.append("SMB connectivity test failed")
        
        # Report results
        print("\n📊 Troubleshooting Results:")
        print("="*30)
        
        if fixes_applied:
            print("✅ Fixes Applied:")
            for fix in fixes_applied:
                print(f"  • {fix}")
        
        if issues_found:
            print("\n⚠️  Issues Found:")
            for issue in issues_found:
                print(f"  • {issue}")
            
            print("\n💡 Manual Steps You May Need:")
            print("  • Check Windows Firewall settings")
            print("  • Ensure Windows and Linux are on same network")
            print(f"  • Try connecting with: \\\\<SERVER_IP>\\{self.share_name}")
            print(f"  • On Windows, try: net use * \\\\<SERVER_IP>\\{self.share_name}")
        else:
            print("\n🎉 All connectivity checks passed!")
        
        return len(issues_found) == 0
    
    def enable_verbose_logging(self):
        """Enable verbose Samba logging for debugging"""
        print("🔍 Enabling verbose Samba logging...")
        
        # Update smb.conf with debug logging
        debug_config = """
# Debug logging configuration
    log level = 3
    debug timestamp = yes
    debug uid = yes
    debug pid = yes
"""
        
        try:
            # Read current config
            with open(self.samba_config, 'r') as f:
                config_content = f.read()
            
            # Replace log level if it exists, otherwise add debug section
            if "log level =" in config_content:
                # Replace existing log level
                import re
                config_content = re.sub(r'log level = \d+', 'log level = 3', config_content)
                # Add debug options if not present
                if "debug timestamp" not in config_content:
                    config_content = config_content.replace(
                        "log level = 3",
                        "log level = 3\n    debug timestamp = yes\n    debug uid = yes\n    debug pid = yes"
                    )
            else:
                # Add debug section to global section
                config_content = config_content.replace(
                    "[global]",
                    f"[global]{debug_config}"
                )
            
            # Write updated config
            with open(self.samba_config, 'w') as f:
                f.write(config_content)
            
            print("✅ Verbose logging enabled")
            
            # Restart services to apply logging changes
            smb_service, nmb_service = self.get_samba_service_names()
            subprocess.run(["systemctl", "restart", smb_service], check=True)
            if nmb_service:
                subprocess.run(["systemctl", "restart", nmb_service], check=True)
            
            print("✅ Samba services restarted with verbose logging")
            
        except Exception as e:
            print(f"⚠️  Failed to enable verbose logging: {e}")
    
    def monitor_samba_logs(self, duration=60):
        """Monitor Samba logs in real-time"""
        print(f"📊 Monitoring Samba logs for {duration} seconds...")
        print("🔍 Look for connection attempts from your Windows client")
        print("⏹️  Press Ctrl+C to stop monitoring early")
        print("-" * 60)
        
        try:
            # Monitor main Samba log
            process = subprocess.Popen(
                ["tail", "-f", "/var/log/samba/log.smbd"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    # Use select to check if data is available
                    if hasattr(select, 'select'):
                        ready, _, _ = select.select([process.stdout], [], [], 1)
                        if ready:
                            line = process.stdout.readline()
                            if line:
                                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                                print(f"[{timestamp}] {line.strip()}")
                    else:
                        time.sleep(1)
                except select.error:
                    break
            
            process.terminate()
            print("\n📊 Log monitoring completed")
            
        except FileNotFoundError:
            print("⚠️  Samba log file not found. Trying alternative locations...")
            alt_logs = [
                "/var/log/samba/log.smb",
                "/var/log/samba/smbd.log",
                "/var/log/samba.log"
            ]
            
            for log_file in alt_logs:
                if os.path.exists(log_file):
                    print(f"📄 Found log at: {log_file}")
                    subprocess.run(["tail", "-n", "20", log_file])
                    break
            else:
                print("❌ No Samba log files found")
        
        except KeyboardInterrupt:
            print("\n⏹️  Log monitoring stopped by user")
            if 'process' in locals():
                process.terminate()
    
    def check_network_connectivity(self):
        """Perform comprehensive network connectivity checks"""
        print("\n🌐 Network Connectivity Diagnostics")
        print("=" * 50)
        
        # Get interface information
        interfaces = self.get_network_interfaces()
        if not interfaces:
            print("❌ No network interfaces found")
            return False
        
        print("📡 Active Network Interfaces:")
        for interface in interfaces:
            print(f"  • {interface['name']}: {interface['ip']} ({interface['cidr']})")
        
        # Check if binding IP is accessible
        bind_ip = self.bind_interfaces
        print(f"\n🔗 Checking binding interface: {bind_ip}")
        
        # Check if the specific IP is reachable
        try:
            result = subprocess.run(["ping", "-c", "1", "-W", "2", bind_ip], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Binding IP {bind_ip} is reachable")
            else:
                print(f"⚠️  Binding IP {bind_ip} may not be reachable")
        except subprocess.CalledProcessError:
            print(f"⚠️  Cannot test binding IP {bind_ip}")
        
        # Check SMB ports
        print("\n🔌 Checking SMB port status:")
        ports_to_check = [445, 139]
        
        for port in ports_to_check:
            try:
                # Check specific IP
                result = subprocess.run(["ss", "-tlnp", f"| grep {bind_ip}:{port}"], 
                                      shell=True, capture_output=True, text=True)
                
                if result.stdout.strip():
                    print(f"  ✅ Port {port}: LISTENING")
                    print(f"     {result.stdout.strip()}")
                else:
                    print(f"  ❌ Port {port}: NOT LISTENING")
            except subprocess.CalledProcessError:
                print(f"  ⚠️  Port {port}: Cannot check")
        
        # Check routing
        print("\n🛣️  Network Routing Information:")
        try:
            result = subprocess.run(["ip", "route", "show"], capture_output=True, text=True, check=True)
            for line in result.stdout.split('\n')[:5]:  # Show first 5 routes
                if line.strip():
                    print(f"  {line}")
        except subprocess.CalledProcessError:
            print("  ⚠️  Cannot retrieve routing information")
        
        return True
    
    def generate_debug_report(self):
        """Generate comprehensive debug report"""
        print("\n📋 Generating Debug Report")
        print("=" * 50)
        
        report_file = f"/tmp/samba_debug_report_{int(time.time())}.txt"
        
        with open(report_file, 'w') as f:
            f.write("SAMBA DEBUG REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.datetime.now()}\n\n")
            
            # System information
            f.write("SYSTEM INFORMATION:\n")
            f.write("-" * 20 + "\n")
            try:
                result = subprocess.run(["uname", "-a"], capture_output=True, text=True, check=True)
                f.write(f"System: {result.stdout}")
            except subprocess.CalledProcessError:
                f.write("System: Unknown\n")
            
            # Samba configuration
            f.write("\nSAMBA CONFIGURATION:\n")
            f.write("-" * 20 + "\n")
            try:
                result = subprocess.run(["testparm", "-s"], capture_output=True, text=True, check=True)
                f.write(result.stdout)
            except subprocess.CalledProcessError as e:
                f.write(f"Configuration test failed: {e}\n")
            
            # Service status
            f.write("\nSERVICE STATUS:\n")
            f.write("-" * 15 + "\n")
            smb_service, nmb_service = self.get_samba_service_names()
            for service in [smb_service, nmb_service]:
                if service:
                    try:
                        result = subprocess.run(["systemctl", "status", service], 
                                              capture_output=True, text=True)
                        f.write(f"{service} status:\n{result.stdout}\n\n")
                    except subprocess.CalledProcessError:
                        f.write(f"{service}: Cannot get status\n")
            
            # Network information
            f.write("NETWORK INFORMATION:\n")
            f.write("-" * 20 + "\n")
            try:
                result = subprocess.run(["ip", "addr", "show"], capture_output=True, text=True, check=True)
                f.write(result.stdout)
            except subprocess.CalledProcessError:
                f.write("Cannot get network information\n")
            
            # Port status
            f.write("\nPORT STATUS:\n")
            f.write("-" * 12 + "\n")
            try:
                result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, check=True)
                # Filter SMB-related ports
                for line in result.stdout.split('\n'):
                    if any(port in line for port in [':445', ':139', ':137', ':138']):
                        f.write(f"{line}\n")
            except subprocess.CalledProcessError:
                f.write("Cannot get port information\n")
            
            # Firewall status
            f.write("\nFIREWALL STATUS:\n")
            f.write("-" * 16 + "\n")
            try:
                result = subprocess.run(["firewall-cmd", "--list-all"], capture_output=True, text=True, check=True)
                f.write(result.stdout)
            except subprocess.CalledProcessError:
                f.write("Cannot get firewall status (firewalld not available)\n")
            
            # Recent Samba logs
            f.write("\nRECENT SAMBA LOGS:\n")
            f.write("-" * 18 + "\n")
            log_files = ["/var/log/samba/log.smbd", "/var/log/samba/log.nmbd"]
            for log_file in log_files:
                if os.path.exists(log_file):
                    f.write(f"\n{log_file}:\n")
                    try:
                        result = subprocess.run(["tail", "-n", "50", log_file], 
                                              capture_output=True, text=True, check=True)
                        f.write(result.stdout)
                    except subprocess.CalledProcessError:
                        f.write("Cannot read log file\n")
        
        print(f"📄 Debug report saved to: {report_file}")
        print("📤 You can share this file for detailed troubleshooting")
        
        # Also display summary
        print("\n📊 Quick Summary:")
        self.check_network_connectivity()
        
        return report_file
    
    def start_debug_session(self):
        """Start interactive debug session"""
        print("\n🔧 Starting Debug Session")
        print("=" * 50)
        
        # Enable verbose logging
        self.enable_verbose_logging()
        
        print("\n🎯 Debug session started!")
        print("📋 Available debug options:")
        print("  1. Monitor logs in real-time")
        print("  2. Check network connectivity") 
        print("  3. Generate debug report")
        print("  4. Test SMB connection")
        print("  5. Exit debug session")
        
        while True:
            try:
                choice = input("\n🔍 Select debug option (1-5): ").strip()
                
                if choice == "1":
                    duration = input("Monitor duration in seconds (default 60): ").strip()
                    try:
                        duration = int(duration) if duration else 60
                    except ValueError:
                        duration = 60
                    self.monitor_samba_logs(duration)
                
                elif choice == "2":
                    self.check_network_connectivity()
                
                elif choice == "3":
                    self.generate_debug_report()
                
                elif choice == "4":
                    self.verify_smb_connectivity()
                
                elif choice == "5":
                    print("👋 Exiting debug session")
                    break
                
                else:
                    print("❌ Invalid choice. Please select 1-5.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Debug session interrupted")
                break
            except EOFError:
                print("\n\n👋 Debug session ended")
                break

    def show_connection_info(self):
        """Display connection information for Windows client"""
        print("\n" + "="*60)
        print("🎉 SMB SERVER SETUP COMPLETE!")
        print("="*60)

        # Display binding information
        print(f"🔗 Binding Interface: {self.bind_interface_name} ({self.bind_interfaces})")
        
        # Get server IP address
        primary_ip = self.bind_interfaces
        print(f"📡 Server IP Address: {primary_ip}")

        print(f"📁 Share Name: {self.share_name}")
        print(f"📂 Share Path: {self.share_path}")
        print("\n🪟 Windows Connection Instructions:")
        print("1. Open File Explorer on Windows")
        print("2. In the address bar, type:")
        print(f"   \\\\{primary_ip}\\{self.share_name}")
        
        print("3. Press Enter")
        print("4. No username/password required (anonymous access)")

        print("\n🔧 Management Commands:")
        print("• Check service status: sudo systemctl status smbd")
        print("• Restart Samba: sudo systemctl restart smbd nmbd")
        print("• View logs: sudo tail -f /var/log/samba/log.smbd")
        print("• Test config: sudo testparm")

        print("\n⚠️  Security Note:")
        print("This setup allows anonymous access to the shared directory.")
        print("Ensure this is appropriate for your network environment.")

    def setup(self):
        """Main setup function"""
        print("🔧 Starting SMB Server Setup...")
        if self.debug_mode:
            print("🐛 Debug mode enabled - verbose logging will be activated")
        print(f"📁 Target directory: {self.share_path}")
        print(f"🏷️  Share name: {self.share_name}")
        print()

        self.check_root_privileges()
        self.check_share_directory()
        self.select_network_binding()
        self.select_smb_version()
        self.install_samba()
        self.backup_samba_config()
        self.create_samba_config()
        self.set_directory_permissions()
        self.configure_firewall()
        self.configure_selinux()
        self.test_configuration()
        self.start_samba_services()
        
        # Run troubleshooting to ensure everything works
        self.troubleshoot_connectivity()
        
        # Check firewall status and show reminders
        self.check_firewall_status()
        
        # Enable verbose logging if debug mode
        if self.debug_mode:
            self.enable_verbose_logging()
        
        self.show_connection_info()
        
        # Important reminders
        print("\n📋 IMPORTANT POST-SETUP REMINDERS:")
        print("=" * 50)
        print("🔥 FIREWALL: If SMB share is not accessible from guest OS:")
        print("   • Check if your network interface is in libvirt zone:")
        print("     sudo firewall-cmd --get-zone-of-interface=virbr55")
        print("   • If yes, add Samba to libvirt zone:")
        print("     sudo firewall-cmd --zone=libvirt --add-service=samba --permanent")
        print("     sudo firewall-cmd --zone=libvirt --add-port=445/tcp --permanent")
        print("     sudo firewall-cmd --zone=libvirt --add-port=139/tcp --permanent")
        print("     sudo firewall-cmd --reload")
        print("🪟 WINDOWS: If Windows can't connect, enable SMB1 client:")
        print("   • PowerShell as Admin: Enable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol-Client")
        print("   • Or: Control Panel → Programs → Turn Windows features on/off → SMB 1.0/CIFS File Sharing Support")
        print("🔍 DEBUGGING: Use --debug flag for detailed troubleshooting")
        print()
        
        # Additional debug info in debug mode
        if self.debug_mode:
            print("\n🐛 DEBUG MODE - Additional Information:")
            print("=" * 50)
            print("🔍 Use the following commands to monitor connections:")
            print("  • Monitor logs: sudo tail -f /var/log/samba/log.smbd")
            print("  • Monitor connections: sudo python3 main.py --monitor") 
            print("  • Generate report: sudo python3 main.py --report")
            print("  • Start debug session: sudo python3 main.py --debug")
            
            # Show current network and port status
            self.check_network_connectivity()


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SMB Server Setup Script")
    parser.add_argument("--debug", action="store_true", 
                       help="Enable debug mode with verbose logging and monitoring")
    parser.add_argument("--monitor", action="store_true",
                       help="Start log monitoring session")
    parser.add_argument("--report", action="store_true",
                       help="Generate debug report only")
    
    args = parser.parse_args()
    
    try:
        setup = SMBServerSetup()
        setup.debug_mode = args.debug
        
        if args.report:
            # Generate debug report only
            setup.generate_debug_report()
            return
            
        if args.monitor:
            # Start monitoring session only
            print("🔍 Starting Samba log monitoring...")
            setup.monitor_samba_logs(300)  # 5 minutes default
            return
        
        if args.debug:
            print("🐛 DEBUG MODE ENABLED")
            print("This will enable verbose logging and provide detailed diagnostics")
            # Run normal setup first
            setup.setup()
            # Then start debug session
            setup.start_debug_session()
        else:
            # Normal setup
            setup.setup()
            
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if setup.debug_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
