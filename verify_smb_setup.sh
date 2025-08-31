#!/bin/bash

# SMB Service Verification Script
# Verifies that Samba is running and bound to the correct interface

echo "🔍 SMB Service Verification"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "OK")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    print_status "ERROR" "This script must be run as root (sudo)"
    exit 1
fi

echo

# 1. Check Samba service status
echo "1. Checking Samba Service Status:"
echo "---------------------------------"

# Check smbd service
if systemctl is-active --quiet smbd 2>/dev/null; then
    print_status "OK" "smbd service is running"
else
    print_status "ERROR" "smbd service is not running"
fi

# Check nmbd service
if systemctl is-active --quiet nmbd 2>/dev/null; then
    print_status "OK" "nmbd service is running"
else
    print_status "WARNING" "nmbd service is not running (optional for NetBIOS name resolution)"
fi

echo

# 2. Check Samba configuration
echo "2. Checking Samba Configuration:"
echo "-------------------------------"

SAMBA_CONFIG="/etc/samba/smb.conf"
if [[ -f "$SAMBA_CONFIG" ]]; then
    print_status "OK" "Samba configuration file exists"

    # Check interfaces configuration
    INTERFACES_CONFIG=$(grep -E "^[[:space:]]*interfaces[[:space:]]*=" "$SAMBA_CONFIG" | head -1)
    if [[ -n "$INTERFACES_CONFIG" ]]; then
        CONFIGURED_INTERFACE=$(echo "$INTERFACES_CONFIG" | sed 's/.*= *//')
        print_status "INFO" "Configured interfaces: $CONFIGURED_INTERFACE"

        # Check bind interfaces only
        BIND_ONLY=$(grep -E "^[[:space:]]*bind interfaces only[[:space:]]*=" "$SAMBA_CONFIG" | head -1)
        if [[ -n "$BIND_ONLY" ]]; then
            BIND_VALUE=$(echo "$BIND_ONLY" | sed 's/.*= *//' | tr '[:upper:]' '[:lower:]')
            if [[ "$BIND_VALUE" == "yes" ]]; then
                print_status "OK" "bind interfaces only = yes"
            else
                print_status "WARNING" "bind interfaces only = $BIND_VALUE (should be yes)"
            fi
        else
            print_status "WARNING" "bind interfaces only not configured"
        fi
    else
        print_status "WARNING" "No interfaces configuration found in Samba config"
        CONFIGURED_INTERFACE="0.0.0.0"
    fi
else
    print_status "ERROR" "Samba configuration file not found"
    exit 1
fi

echo

# 3. Check all SMB-related listening ports
echo "3. Checking All SMB-Related Listening Ports:"
echo "--------------------------------------------"

# Check all SMB-related ports
SMB_PORTS=(445 139 137 138)
for port in "${SMB_PORTS[@]}"; do
    PORT_LISTENING=$(ss -tulpn | grep ":$port ")
    if [[ -n "$PORT_LISTENING" ]]; then
        case $port in
            445)
                print_status "OK" "SMB port $port (SMB2/3) is listening"
                ;;
            139)
                print_status "OK" "NetBIOS port $port (SMB1) is listening"
                ;;
            137)
                print_status "OK" "NetBIOS port $port (name service) is listening"
                ;;
            138)
                print_status "OK" "NetBIOS port $port (datagram service) is listening"
                ;;
        esac

        # Show detailed process information
        echo "$PORT_LISTENING" | while read -r line; do
            addr=$(echo "$line" | awk '{print $5}')
            process_info=$(echo "$line" | awk '{print $7}')
            pid=$(echo "$process_info" | sed 's/.*pid=//' | sed 's/,.*//')
            process=$(echo "$process_info" | sed 's/users:(("//' | sed 's/".*//')

            if [[ "$addr" == "0.0.0.0:$port" ]]; then
                print_status "WARNING" "  └─ Listening on 0.0.0.0:$port - Process: $process (PID: $pid)"
            elif [[ "$addr" == "::$port" ]]; then
                print_status "INFO" "  └─ Listening on [::]:$port - Process: $process (PID: $pid)"
            else
                print_status "OK" "  └─ Listening on $addr - Process: $process (PID: $pid)"
            fi
        done
    else
        case $port in
            445)
                print_status "ERROR" "SMB port $port is not listening"
                ;;
            139)
                print_status "INFO" "NetBIOS port $port is not listening (normal if nmbd not running)"
                ;;
            137|138)
                print_status "INFO" "NetBIOS port $port is not listening"
                ;;
        esac
    fi
done

echo

# 4. Verify configuration matches actual listening
echo "4. Configuration vs Actual Listening:"
echo "------------------------------------"

SMB_LISTENING=$(ss -tulpn | grep ':445 ')
if [[ -n "$SMB_LISTENING" ]]; then
    # Check if configuration matches reality
    if [[ "$CONFIGURED_INTERFACE" != "0.0.0.0" && "$CONFIGURED_INTERFACE" != "lo" ]]; then
        # Check if any address is 0.0.0.0
        if echo "$SMB_LISTENING" | grep -q "0.0.0.0:445"; then
            print_status "ERROR" "Configuration specifies specific interface but service is listening on all interfaces"
            print_status "INFO" "This usually means the interface name in Samba config is incorrect"
            print_status "INFO" "Check that the interface name in /etc/samba/smb.conf matches: $CONFIGURED_INTERFACE"
        else
            print_status "OK" "Service is properly bound to specific interface(s)"
        fi
    elif [[ "$CONFIGURED_INTERFACE" == "0.0.0.0" ]]; then
        if echo "$SMB_LISTENING" | grep -q "0.0.0.0:445"; then
            print_status "OK" "Service is correctly listening on all interfaces as configured"
        else
            print_status "WARNING" "Configuration allows all interfaces but service is bound to specific ones"
        fi
    fi
fi

echo

# 5. Network interface information
echo "5. Network Interface Information:"
echo "---------------------------------"

echo "Available network interfaces:"
ip -4 addr show | grep -E "^[0-9]+:" | while read -r line; do
    iface=$(echo "$line" | awk '{print $2}' | sed 's/://')
    ip_info=$(ip -4 addr show "$iface" | grep "inet " | awk '{print $2}')
    if [[ -n "$ip_info" ]]; then
        echo "   $iface: $ip_info"
    fi
done

echo

# 6. Samba Process Information
echo "6. Samba Process Information:"
echo "----------------------------"

echo "Samba-related processes:"
ps aux | grep -E "smbd|nmbd|samba" | grep -v grep | while read -r line; do
    pid=$(echo "$line" | awk '{print $2}')
    process=$(echo "$line" | awk '{print $11}')
    args=$(echo "$line" | awk '{for(i=12;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/ $//')
    echo "   PID $pid: $process $args"
done

echo

# 7. Recommendations
echo "7. Recommendations:"
echo "------------------"

if [[ -n "$SMB_LISTENING" ]]; then
    if echo "$SMB_LISTENING" | grep -q "0.0.0.0:445"; then
        print_status "INFO" "Consider configuring Samba to bind to a specific interface for better security"
        print_status "INFO" "Update /etc/samba/smb.conf with: interfaces = <interface_name>"
        print_status "INFO" "And add: bind interfaces only = yes"
        print_status "INFO" "Current configured interface: $CONFIGURED_INTERFACE"
    else
        print_status "OK" "SMB service is properly configured for specific interface binding"
    fi
else
    print_status "ERROR" "SMB service is not running. Start with: sudo systemctl start smbd"
fi

echo
print_status "INFO" "Verification complete"
