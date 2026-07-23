from machine import Pin, ADC
import network
import socket
import time
import dht
import gc
gc.collect()

# Configured as an open network with NO password required
ap_ssid = 'Meteo Mali dol'

# Initialize DHT11 globally to prevent memory leaks and timing issues
sensor = dht.DHT11(Pin(4))

def setup_captive_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    
    # authmode=0 creates an open network (no password)
    ap.config(essid=ap_ssid, authmode=0)
    
    print('Captive Access Point active!')
    print('Connect to Wi-Fi:', ap_ssid)
    print('IP Configuration:', ap.ifconfig())

def run_dns_server():
    """
    A minimal DNS Server that intercepts network requests 
    and redirects them straight to the ESP32 IP address (192.168.4.1).
    """
    dns_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dns_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    dns_sock.bind(('', 53))
    dns_sock.setblocking(False)  # Non-blocking so it doesn't freeze the main loop
    print('DNS Hijacker running on port 53...')
    return dns_sock

def handle_dns(dns_sock):
    try:
        data, addr = dns_sock.recvfrom(512)
        packet_id = data[:2]
        # Construct a raw spoofed DNS response pointing to 192.168.4.1
        response = packet_id + b'\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00'
        idx = 12
        while data[idx] != 0:
            idx += data[idx] + 1
        idx += 5  
        response += data[12:idx]
        response += b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x0a\x00\x04\xc0\xa8\x04\x01'
        dns_sock.sendto(response, addr)
    except OSError:
        pass

def read_temp():
    try:
        sensor.measure()
        temp_c = sensor.temperature()
        humidity = sensor.humidity()
        return temp_c, humidity
    except OSError as e:
        print("Failed to read data from DHT11 sensor.")
        return 0, 0  # Fallback values to keep server running

def web_page(temp, humidity):
    # Your exact requested HTML layout with a mobile viewport fix added for captive windows
    html_str = f"""<html>
<head>
    <title>Meteo postaja "Mali dol"</title>
    <meta http-equiv="refresh" content="5">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <h1 style="font-size: 3rem;">Meteo postaja "Mali dol"</h1>
    <p style="font-size: 30px;"><strong>Temperatura: {temp} *C</strong></p>
    <p style="font-size: 30px;"><strong>Vlaga: {humidity} %</strong></p>
    <p style="font-size: 10px;"><strong>Ovo je testna postaja u nastajanju. lp, Edvard!!! Moreš gledat, nemoj dirat!</strong></p>
</body>
<style>
    html {{ text-align: center; font-family: Arial; }}
</style>
</html>"""
    return html_str

def main():
    setup_captive_ap()
    dns_sock = run_dns_server()
    
    # Set up HTTP web server
    http_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    http_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    http_sock.bind(('', 80))
    http_sock.listen(5)
    http_sock.setblocking(False)  # Non-blocking to allow background looping
    print('HTTP Server running on port 80...')
    
    while True:
        # 1. Listen for background DNS requests to trigger the Captive Portal pop-up
        handle_dns(dns_sock)
        
        # 2. Listen for incoming web page requests
        try:
            client, addr = http_sock.accept()
            print('Client %s is connected' % str(addr))
            request = client.recv(1024)
            
            temp, humidity = read_temp()
            response = web_page(temp, humidity)
            
            client.send('HTTP/1.1 200 OK\r\n')
            client.send('Content-Type: text/html\r\n')
            client.send('Connection: close\r\n\r\n')
            client.sendall(response.encode('utf-8'))
            client.close()
        except OSError:
            pass  # No incoming web clients in this loop cycle
            
        time.sleep(0.02)  # Short delay to prevent CPU overheating

if __name__ == "__main__":
    main()
