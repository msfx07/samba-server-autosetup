#!/bin/bash

# Configuration - modify these as needed
SERVER_IP="10.10.55.1"
SHARE_NAME="shared"
INTERFACE="virbr55"

echo "=== SMB Connectivity Test ==="
echo "Date: $(date)"
echo "Server IP: $SERVER_IP"
echo "Share Name: $SHARE_NAME"
echo

echo "1. Testing SMB service status:"
sudo systemctl status smb --no-pager | grep -E "(Active|Main PID)"
echo

echo "2. Testing port binding:"
sudo ss -tlnp | grep :445
echo

echo "3. Testing SMB1 connectivity:"
smbclient -L $SERVER_IP -N --option='client min protocol=CORE' 2>/dev/null || echo "SMB1 test failed"
echo

echo "4. Testing SMB2 connectivity:"
smbclient -L $SERVER_IP -N --option='client min protocol=SMB2' 2>/dev/null || echo "SMB2 test failed"
echo

echo "5. Testing shared directory access:"
smbclient //$SERVER_IP/$SHARE_NAME -N -c 'ls' 2>/dev/null || echo "Shared directory access failed"
echo

echo "6. Network interfaces and IPs:"
ip addr show $INTERFACE 2>/dev/null | grep -E "inet |UP"
echo

echo "7. Active connections on guest network:"
ip neigh show | grep "${SERVER_IP%.*}"
echo

echo "8. Firewall status for SMB ports:"
sudo firewall-cmd --list-ports 2>/dev/null | grep -E "445|139" || echo "Firewall check failed"
echo

echo "9. Recent Samba log entries:"
sudo tail -5 /var/log/samba/log.smbd 2>/dev/null || echo "No recent logs"
echo

echo "=== Test completed ==="
echo "If Windows still can't connect, try:"
echo "  - \\\\$SERVER_IP\\$SHARE_NAME"
echo "  - net use Z: \\\\$SERVER_IP\\$SHARE_NAME"
echo "  - Enable SMB1 in Windows features"
