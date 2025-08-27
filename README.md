# SMB Server Set- 🔧 Automatic Samba installation and configuration
- 🔓 Anonymous access (no username/password required)
- 📁 Configurable shared directory (default: `/srv/shared`)
- 🪟 Windows-compatible SMB protocol
- 🔐 **SMB version selection (SMBv1/SMBv2/SMBv3) with auto-timeout**
- 🛡️ Proper permissions and security settings
- 📋 Automatic backup of existing configuration
- ✅ Configuration validation
- 🌐 **Network interface binding selection with auto-timeout**
- 🔍 **Comprehensive troubleshooting and helper scripts**nux

A comprehensive Python script that automatically configures a production-ready Samba (SMB) server on Linux with anonymous access. Designed to share directories (default: `/srv/shared`) for seamless file sharing between Linux host and Windows Guest OS environments.

## 🎯 Purpose

This tool was created to solve the common challenge of setting up reliable file sharing between Linux hosts and Windows guest operating systems in virtualized environments. It automates the entire Samba server configuration process, handles complex firewall setups (including libvirt zones), and provides comprehensive troubleshooting capabilities.

### 🔧 Key Use Cases:
- **Virtualization Environments**: Share files between Linux host and Windows/Linux VMs
- **Development Setups**: Quick SMB server deployment for testing and development
- **Home Lab Networks**: Secure anonymous file sharing on isolated networks
- **Cross-Platform Integration**: Bridge Linux and Windows file systems seamlessly

## Features

- 🔧 Automatic Samba installation and configuration
- 🔓 Anonymous access (no username/password required)
- 📁 Configurable shared directory (default: `/srv/shared`)
- 🪟 Windows-compatible SMB protocol
- � **SMB version selection (SMBv1/SMBv2/SMBv3) with auto-timeout**
- �🛡️ Proper permissions and security settings
- 📋 Automatic backup of existing configuration
- ✅ Configuration validation
- 🌐 **Network interface binding selection with auto-timeout**

## Prerequisites

- Linux system with supported package manager:
  - **Debian/Ubuntu**: `apt`
  - **Fedora/RHEL/CentOS**: `dnf` or `yum`
  - **Arch Linux**: `pacman`
  - **openSUSE**: `zypper`
- Root/sudo privileges
- Network connectivity between host and guest OS

## Usage

### 1. Basic Setup

```bash
sudo python3 main.py
```

### 2. Debug Mode (Recommended for Troubleshooting)

```bash
# Full setup with debug mode
sudo python3 main.py --debug

# Just monitor logs
sudo python3 main.py --monitor

# Generate debug report only
sudo python3 main.py --report
```

**Debug mode features:**
- 🔍 **Verbose Samba logging** - Detailed connection logs
- 📊 **Real-time log monitoring** - Watch connection attempts live
- 🌐 **Network diagnostics** - Check ports, interfaces, routing
- 📋 **Comprehensive debug report** - Complete system analysis
- 🎯 **Interactive debug session** - Step-by-step troubleshooting

### 3. Setup Process

The script will:
- Install Samba if not already installed
- Create the shared directory if it doesn't exist (default: `/srv/shared`)
- **Detect available network interfaces and let you choose binding**
- **Select SMB protocol version for compatibility (SMBv1/SMBv2/SMBv3)**
- Configure Samba for anonymous access
- Set proper permissions
- Start and enable Samba services
- Display connection information

### 4. Network Interface Selection

During setup, the script will:
1. **Detect all available network interfaces** (physical, virtual, bridge)
2. **Display options** with IP addresses
3. **Provide 60-second countdown** for user selection
4. **Auto-select binding to all interfaces (0.0.0.0)** if no input provided

**Example interface selection:**
```
📡 Available network interfaces:

  [0] Bind to all interfaces (0.0.0.0) - Default
  [1] Bind to eth0 (192.168.1.100)
  [2] Bind to wlan0 (192.168.1.101)
  [3] Bind to virbr0 (192.168.122.1)

🕐 You have 60 seconds to choose an option.
⏰ If no input is provided, option [0] will be selected automatically.

⌛ Select option [0-3] (60s remaining): 
```

### 5. SMB Protocol Version Selection

The script allows you to choose the SMB protocol version for compatibility:

1. **SMBv1 (NT1) to SMBv3** - Default, maximum compatibility
   - ✅ Compatible with Windows XP and all newer versions
   - ⚠️ Less secure but most compatible
   - 🎯 Recommended for mixed environments with older systems

2. **SMBv2 to SMBv3** - Good security/compatibility balance
   - ✅ Compatible with Windows 7 and newer
   - 🔒 More secure than SMBv1
   - 🎯 Recommended for modern environments

3. **SMBv3 Only** - Maximum security
   - ✅ Compatible with Windows 8 and newer only
   - 🔒 Most secure option
   - 🎯 Recommended for high-security environments

**Auto-selection**: If no choice is made within 60 seconds, SMBv1 compatibility is automatically selected for maximum compatibility.

### 6. Connect from Windows

1. Open **File Explorer** on your Windows Guest OS
2. In the address bar, type: `\\<SERVER_IP>\shared`
   - Replace `<SERVER_IP>` with the IP address shown by the script
3. Press **Enter**
4. The shared folder should open without requiring credentials

## Helper Scripts

### 🐧 Linux Connectivity Testing (`test_connectivity.sh`)

A comprehensive diagnostic script to test SMB server functionality and connectivity from the Linux side.

**What it checks**:
- ✅ SMB service status and process information
- ✅ Port binding verification (445, 139)
- ✅ SMB1 and SMB2 protocol connectivity
- ✅ Share accessibility testing
- ✅ Network interface configuration
- ✅ Firewall port status
- ✅ Recent Samba log entries
- ✅ Active network connections

**Usage**:
```bash
# Make executable and run
chmod +x test_connectivity.sh
./test_connectivity.sh
```

**Sample output**:
```
=== SMB Connectivity Test ===
1. Testing SMB service status:
   Active: active (running)
2. Testing port binding:
   *:445 LISTEN
3. Testing SMB1 connectivity:
   ✅ SMB1 connection successful
4. Testing share access:
   ✅ Share accessible
```

### 🪟 Windows Client Configuration (`windows_smb_commands.ps1`)

PowerShell commands to configure Windows clients for SMB connectivity, especially useful for older Windows versions or systems with strict security policies.

**What it configures**:
- ✅ Enables SMB1 protocol client (for older Windows compatibility)
- ✅ Configures SMB security settings for anonymous shares
- ✅ Disables SMB signing requirements
- ✅ Provides connectivity testing commands
- ✅ Includes drive mapping examples

**Usage**:
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\windows_smb_commands.ps1
```

**Key commands included**:
```powershell
# Enable SMB1 for maximum compatibility
Enable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol-Client

# Configure for anonymous shares
Set-SmbClientConfiguration -RequireSecuritySignature $false -Force

# Test connectivity
ping <SERVER_IP>
net use Z: \\<SERVER_IP>\shared
```

**When to use these scripts**:
- 🔧 **After setup**: Run `test_connectivity.sh` to verify everything is working
- 🐛 **Troubleshooting**: Use both scripts when Windows cannot connect
- 📊 **Monitoring**: Regular checks with `test_connectivity.sh`
- 🪟 **Windows issues**: Use `windows_smb_commands.ps1` for client-side problems

## Configuration Details

### Share Settings
- **Share Name**: `shared`
- **Share Path**: `/srv/shared` (configurable)
- **Access**: Anonymous (guest access enabled)
- **Permissions**: Read/Write for everyone

### Security Notes
⚠️ **Important**: This configuration allows anonymous access to the shared directory. This is suitable for:
- Isolated networks
- Development environments
- Trusted local networks

**Do not use this configuration on production systems or networks exposed to the internet.**

## Troubleshooting

The script includes automatic troubleshooting that runs during setup to fix common connectivity issues:

### Automatic Fixes Applied
- **Firewall Configuration**: Automatically opens SMB ports (445, 139, 137, 138)
- **SELinux Configuration**: Sets proper contexts for Samba shares
- **Service Management**: Ensures all Samba services are running
- **Connectivity Testing**: Verifies SMB server accessibility

### Common Issues

**🚀 Quick Troubleshooting**: Use the included helper scripts for faster diagnosis:
- **Linux side**: `./test_connectivity.sh` - Comprehensive server diagnostics
- **Windows side**: `.\windows_smb_commands.ps1` - Client configuration commands

1. **Windows Cannot See \\\\SERVER_IP\\shared**
   
   **Automatic fixes applied by script:**
   - ✅ Firewall ports opened for Samba
   - ✅ SELinux contexts configured
   - ✅ Services restarted if needed
   
   **Manual steps if still not working:**
   - **Use Windows helper script**: Run `windows_smb_commands.ps1` in PowerShell as Administrator
   - Check Windows Firewall settings
   - Ensure both systems are on the same network
   - Try: `net use Z: \\\\<SERVER_IP>\\shared` in Windows Command Prompt
   - Verify IP connectivity: `ping <SERVER_IP>` from Windows
   - **SMB Version Issues**: If using older Windows (XP/7), ensure SMBv1 was selected during setup

2. **Permission Denied**
   - Ensure you're running the script with `sudo`
   - Check that the shared directory has proper permissions
   - Script automatically tries alternative permission setups

3. **Service Failed to Start**
   - Script automatically detects correct service names for your distribution
   - Check Samba configuration: `sudo testparm`
   - View logs:
     - Debian/Ubuntu: `sudo journalctl -u smbd`
     - Red Hat/Fedora: `sudo journalctl -u smb`

4. **SELinux Blocking Access**
   - Script automatically configures SELinux contexts
   - Manual check: `sudo setsebool -P samba_enable_home_dirs on`
   - Verify context: `ls -laZ /srv/shared`

### Useful Commands

```bash
# Check Samba service status (choose based on your distribution)
# Debian/Ubuntu:
sudo systemctl status smbd nmbd
# Red Hat/Fedora/CentOS:
sudo systemctl status smb nmb

# Restart Samba services (choose based on your distribution)  
# Debian/Ubuntu:
sudo systemctl restart smbd nmbd
# Red Hat/Fedora/CentOS:
sudo systemctl restart smb nmb

# Test configuration
sudo testparm

# View Samba logs
sudo tail -f /var/log/samba/log.smbd

# Check network connections
sudo netstat -tlnp | grep :445
```

### Firewall Configuration

If you have a firewall enabled, you may need to allow SMB traffic:

```bash
# For UFW (Ubuntu)
sudo ufw allow 445/tcp
sudo ufw allow 139/tcp
sudo ufw allow 137:138/udp

# For firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-service=samba
sudo firewall-cmd --reload
```

## Configuration Backup

The script automatically creates a backup of your existing Samba configuration at:
`/etc/samba/smb.conf.backup`

To restore the original configuration:
```bash
sudo cp /etc/samba/smb.conf.backup /etc/samba/smb.conf
sudo systemctl restart smbd nmbd
```

## File Structure

```
setup-smbd-server-linux/
├── main.py                    # Main SMB server setup and troubleshooting script
├── README.md                  # Comprehensive documentation and usage guide
├── .gitignore                 # Git ignore rules for Python development
├── test_connectivity.sh       # Linux connectivity testing script
└── windows_smb_commands.ps1   # Windows PowerShell configuration commands
```

### 📁 File Descriptions

#### `main.py` - Core Setup Script
**Purpose**: Complete SMB server automation and troubleshooting tool
**Size**: ~1,400 lines of robust Python code

**Key Components**:
- **`SMBServerSetup` Class**: Main orchestrator handling entire setup workflow
- **Multi-Distribution Support**: Automated package manager detection (apt, dnf, yum, pacman, zypper)
- **Network Interface Management**: Auto-detection and binding configuration for physical/virtual networks
- **Firewall Automation**: Advanced firewall configuration with libvirt zone detection
- **SELinux Integration**: Automatic security context configuration
- **Debug & Monitoring**: Real-time log monitoring and comprehensive diagnostics
- **Troubleshooting Engine**: Automated connectivity testing and issue resolution

**Core Methods**:
```python
setup()                    # Main setup orchestrator
configure_firewall()       # Advanced firewall configuration
troubleshoot_connectivity() # Comprehensive connectivity testing
monitor_logs()             # Real-time Samba log monitoring
generate_debug_report()    # System diagnostics and analysis
```

**Features**:
- ✅ **Automatic Installation**: Detects and installs Samba on any supported Linux distribution
- ✅ **Smart Configuration**: Generates optimized `smb.conf` with anonymous access
- ✅ **Network Binding**: Interactive network interface selection with auto-timeout
- ✅ **Firewall Intelligence**: Detects libvirt zones and configures appropriate firewall rules
- ✅ **SELinux Compatibility**: Automatic security context management
- ✅ **Service Management**: Cross-distribution service handling (smbd/smb, nmbd/nmb)
- ✅ **Backup & Recovery**: Automatic configuration backup before changes
- ✅ **Comprehensive Testing**: Built-in connectivity and configuration validation
- ✅ **Debug Mode**: Verbose logging, real-time monitoring, and detailed diagnostics

#### `README.md` - Documentation
**Purpose**: Complete user guide and troubleshooting reference
**Content**: Installation, usage, troubleshooting, and technical details

#### `.gitignore` - Version Control Configuration
**Purpose**: Excludes Python cache files, IDE settings, logs, and Samba backups from version control
**Includes**: Python-specific patterns, development tools, project-specific exclusions

#### `test_connectivity.sh` - Linux Connectivity Testing Script
**Purpose**: Comprehensive SMB connectivity diagnostics for Linux systems
**Features**:
- SMB service status verification
- Port binding and network interface checks
- SMB1/SMB2 protocol testing
- Share accessibility testing
- Firewall configuration verification
- Recent log analysis
- Network neighbor discovery

**Usage**:
```bash
# Make executable and run
chmod +x test_connectivity.sh
./test_connectivity.sh
```

**When to use**: Run this script if you're experiencing connectivity issues or want to verify SMB server status after setup.

#### `windows_smb_commands.ps1` - Windows PowerShell Configuration Script
**Purpose**: Windows client-side SMB configuration commands for troubleshooting
**Features**:
- Enable SMB1 protocol client support
- Configure SMB security settings for anonymous shares
- Test network connectivity to SMB server
- Provide drive mapping commands
- Guest authentication configuration

**Usage**:
```powershell
# Run PowerShell as Administrator, then:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\windows_smb_commands.ps1
```

**When to use**: Use these commands on Windows Guest OS when you cannot connect to the SMB share, especially with older Windows versions or strict security settings.

## 🏗️ Script Architecture

### Class Structure
```
SMBServerSetup
├── __init__()                 # Initialize configuration and paths
├── setup()                    # Main setup workflow coordinator
├── check_root_privileges()    # Security validation
├── detect_distribution()      # OS and package manager detection
├── install_samba()           # Multi-distribution Samba installation
├── get_network_interfaces()  # Network interface discovery
├── select_network_binding()  # Interactive interface selection
├── create_samba_config()     # Generate optimized smb.conf
├── configure_firewall()      # Advanced firewall management
├── configure_selinux()       # SELinux security contexts
├── start_samba_services()    # Cross-distribution service management
├── troubleshoot_connectivity() # Automated diagnostics
├── monitor_logs()            # Real-time log monitoring
└── generate_debug_report()   # Comprehensive system analysis
```

### Advanced Features

#### 🔥 Intelligent Firewall Management
- **Zone Detection**: Automatically identifies libvirt, public, and custom firewall zones
- **Multi-Zone Configuration**: Configures Samba access across all relevant zones
- **Fallback Support**: Handles firewalld, UFW, and iptables
- **Verification**: Confirms firewall rules after application

#### 🌐 Network Interface Intelligence
- **Auto-Discovery**: Detects physical, virtual, and bridge interfaces
- **Smart Binding**: Recommends optimal interface binding based on network topology
- **Timeout Handling**: 60-second auto-selection for unattended deployments
- **IP Address Display**: Shows interface IPs for easy client configuration

#### 🐛 Comprehensive Debugging
- **Log Monitoring**: Real-time Samba log analysis with filtering
- **Network Diagnostics**: Port scanning, interface testing, routing analysis
- **Service Validation**: Process status, configuration testing, connectivity verification
- **System Analysis**: Complete environment assessment and recommendations

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Samba logs for error messages
3. Verify network connectivity between systems
4. Ensure proper permissions on the shared directory

---

**Note**: This script now supports multiple Linux distributions including Ubuntu/Debian (apt), Fedora/RHEL/CentOS (dnf/yum), Arch Linux (pacman), and openSUSE (zypper). The script automatically detects your distribution and uses the appropriate package manager.
