# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2025-09-07

### Fixed
- **Windows 10 Write Access**: Resolved read-only access issue for Windows 10 clients
  - Removed problematic `force user` and `force group` settings that caused permission conflicts
  - Updated create/directory masks from 0755 to 0777 for full permissions
  - Added `force create mode` and `force directory mode` settings
  - Fixed recursive permission setting for existing files and directories
  - Ensured proper anonymous guest access with write permissions

### Changed
- **Permission Management**: Enhanced permission setup to be recursive on all files and directories
- **Samba Configuration**: Improved share configuration for better Windows compatibility

## [1.0.1] - 2025-09-07

### Added
- **uv Package Manager Support**: Added comprehensive uv integration for faster Python execution
  - Created `setup_up.sh` script for automated uv installation
  - Added uv usage instructions in README
  - Support for uv virtual environments
- **Comprehensive Verification Script**: Created `verify_smb_setup.sh` for detailed SMB service verification
  - Real-time port monitoring and process information
  - Configuration validation and troubleshooting
  - Network interface binding verification

### Fixed
- **Firewall Detection**: Improved OS-specific firewall handling
  - Fixed firewalld detection on Debian systems
  - Added support for UFW, iptables, and SuSEfirewall2
  - Graceful fallback when firewall commands are not available
- **Security Improvements**: Removed insecure 0.0.0.0 default binding
  - Proper network interface selection with auto-timeout
  - Enhanced interface binding verification
- **Bug Fixes**: Fixed various syntax and parsing issues
  - Corrected awk column parsing in verification script
  - Improved error handling for missing commands

### Changed
- **Documentation**: Updated README with uv integration and verification guide
- **Code Quality**: Enhanced firewall status checking with OS detection
- **User Experience**: Improved debug output and troubleshooting information

### Security
- **Interface Binding**: Removed default 0.0.0.0 binding for better security
- **Firewall Configuration**: Enhanced firewall detection and configuration
- **Process Validation**: Added comprehensive service and process verification

## [1.0.0] - 2025-08-31

### Added
- Initial release of SMB Server Auto Setup
- Automatic Samba installation and configuration
- Anonymous access setup for file sharing
- Network interface detection and selection
- Firewall configuration for SMB services
- Comprehensive troubleshooting and debug features
- Cross-platform Linux support (Debian, Ubuntu, CentOS, Fedora, etc.)
- SELinux configuration support
- Real-time log monitoring
- Debug report generation

### Features
- 🔧 Automatic Samba server setup
- 🔓 Anonymous file sharing
- 📁 Configurable shared directories
- 🪟 Windows-compatible SMB protocol
- 🌐 Network interface binding
- 🔥 Automatic firewall configuration
- 🔍 Built-in troubleshooting tools
- 📋 Debug report generation
- 🎯 Interactive setup process
