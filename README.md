# ESP32-Captive-Portal-Weather-Station

BUILDING AN ESP32 CAPTIVE PORTAL WEATHER STATION 
================================================================================

1. PROJECT OVERVIEW
--------------------------------------------------------------------------------
This project transforms your ESP32 into a standalone local weather broadcasting
hub. It creates an open Wi-Fi network named "Meteo Mali dol". When a user connects
with a smartphone, tablet, or laptop, a Captive Portal (system login pop-up window)
automatically forces open. It displays live temperature and humidity data read from
a DHT11 sensor directly inside that system window without needing any active
internet connection or cellular data.

2. LOGICAL CODE BREAKDOWN
--------------------------------------------------------------------------------

PART 1: IMPORTS AND MEMORY PREPARATION
--------------------------------------
Code:
  from machine import Pin, ADC
  import network
  import socket
  import time
  import dht
  import gc
  gc.collect()

Explanation:
  * machine: The essential core MicroPython module that provides direct, low-level
    access to the physical hardware pins on your ESP32 development board.
  * network: Handles the underlying Wi-Fi radio drivers. It allows configuration
    of the ESP32 either as a client (Station mode) or as a router (Access Point).
  * socket: Provides access to standard BSD socket interfaces. This is what handles
    raw incoming and outgoing Internet Protocol (IP) data streams.
  * time: Used to implement exact delays and ticks required for the hardware loop.
  * dht: A built-in optimized driver designed to interface with the unique data-bus
    timing protocol used by DHT11 and DHT22 sensors.
  * gc.collect(): Explicitly forces the Garbage Collector to run. Microcontrollers
    have highly limited RAM. By invoking this right at boot-up, you sweep out loose,
    fragmented variables from memory, drastically reducing the risk of
    "MemoryError" crashes during execution.


PART 2: CONFIGURATION & GLOBAL SENSOR INITIALIZATION
----------------------------------------------------
Code:
  ap_ssid = 'Meteo Mali dol'
  sensor = dht.DHT11(Pin(4))

Explanation:
  * ap_ssid: The broadcast name of your Wi-Fi network. It is kept brief to stay
    firmly under the strict 32-character maximum limit defined by global 802.11
    wireless networking standards.
  * dht.DHT11(Pin(4)): This constructs a global instance of the sensor object,
    telling the firmware that the physical data line of your DHT11 module is
    plugged directly into GPIO Pin 4. Initializing this globally exactly once prevents
    re-allocation memory leaks that would otherwise freeze the system after a
    few hours of operation.


PART 3: THE CAPTIVE ACCESS POINT SETUP
--------------------------------------
Code:
  def setup_captive_ap():
      ap = network.WLAN(network.AP_IF)
      ap.active(True)
      ap.config(essid=ap_ssid, authmode=0)

Explanation:
  * network.WLAN(network.AP_IF): Configures the ESP32 radio stack to operate in
    "Access Point" (AP) mode, meaning it generates its own independent local Wi-Fi
    network instead of attempting to connect to an existing home router.
  * ap.active(True): Powers up the internal physical radio amplifier and starts
    broadcasting the wireless signal.
  * authmode=0: Sets the security level of the network to wide open (no password).
    This removes any configuration friction, ensuring that anyone can instantly
    connect and trigger the weather dashboard.


PART 4: THE DNS INTERCEPTOR CAPTURE ENGINE
------------------------------------------
Code:
  def run_dns_server():
      dns_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      dns_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      dns_sock.bind(('', 53))
      dns_sock.setblocking(False)
      return dns_sock

Explanation:
  * socket.AF_INET, socket.SOCK_DGRAM: Instantiates a standard UDP socket. Domain
    Name System (DNS) requests universally communicate using light UDP packets.
  * bind(('', 53)): Commands the socket to intercept traffic arriving on Port 53,
    the internationally reserved networking port exclusively designated for DNS.
  * setblocking(False): This is arguably the most critical configuration line. It
    makes the socket non-blocking. If a background loop cycle runs and no client is
    actively querying a website, the code bypasses it instantly. If left at its
    default blocking state, the code would completely freeze on this line forever
    waiting for a user, breaking the rest of your web server logic.


PART 5: THE DNS SPOOFING TRICK (CAPTIVE PORTAL TRIGGER)
--------------------------------------------------------
Code:
  def handle_dns(dns_sock):
      try:
          data, addr = dns_sock.recvfrom(512)
          packet_id = data[:2]
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

Explanation:
  * The Trap: When a modern smartphone connects to any Wi-Fi network, its underlying
    operating system immediately fires hidden background DNS requests to check if
    internet backhaul exists (e.g., trying to resolve apple.com or google.com).
  * The Interception: This function intercepts that packet, slices out the specific
    transaction identifier (`data[:2]`), and dynamically stitches together a fake
    binary DNS response packet header.
  * The Redirection: The explicit byte string `\xc0\xa8\x04\x01` decodes directly
    to the hardcoded IP address 192.168.4.1 (the default IP of the ESP32 Access Point).
    The phone is completely fooled into believing your ESP32 is the server it was
    looking for, forcing the system's captive portal browser window to pop open.


PART 6: RESILIENT SENSOR MEASUREMENT
------------------------------------
Code:
  def read_temp():
      try:
          sensor.measure()
          temp_c = sensor.temperature()
          humidity = sensor.humidity()
          return temp_c, humidity
      except OSError as e:
          print("Failed to read data from DHT11 sensor.")
          return 0, 0

Explanation:
  * sensor.measure(): Pulls the physical pin low and releases it to execute a strict,
    time-sensitive hardware data handshake with the DHT11 module.
  * try / except OSError: The DHT11 operates on an unshielded single-wire serial
    interface that is highly susceptible to electrical interference, loose jumper
    wires, or minor power dips. If the pulse timing fails, the hardware driver throws
    an OSError. Wrapping this in a protective error boundary avoids crashing the
    entire application; instead, it outputs fallback values (0, 0) and keeps the
    captive server online.


PART 7: THE METEO DISPLAY COMPILER
----------------------------------
Code:
  def web_page(temp, humidity):
      html_str = f"""<html>..."""
      return html_str

Explanation:
  * F-String Integration: The `f"""` declaration tells Python to compile an
    expression-injected string. This permits the insertion of active live metrics
    directly into raw structural HTML layout blocks via `{temp}` and `{humidity}` keys.
  * Mobile Screen Scale Optimization: The included `<meta name="viewport" content="width=device-width, initial-scale=1">`
    instruction forces the browser layout engine inside system modal pop-ups to
    render text cleanly without tiny microscopic sizing.
  * Automated Refreshing: The instruction `<meta http-equiv="refresh" content="5">`
    forces the phone to clear its rendering buffer and request a fresh data stream
    every 5 seconds, keeping the displayed dashboard accurate without manual scrolling.


PART 8: CORE RUNTIME EXECUTION MAIN LOOP
----------------------------------------
Code:
  def main():
      setup_captive_ap()
      dns_sock = run_dns_server()
     
      http_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      http_sock.bind(('', 80))
      http_sock.listen(5)
      http_sock.setblocking(False)

Explanation:
  * socket.SOCK_STREAM: Opens an entirely different type of transmission path: a
    connection-oriented TCP socket, which is the foundational standard for standard
    web browsing (HTTP).
  * bind(('', 80)): Registers the server to track communication moving across
    Port 80 (the globally standard unsecured clear-text web port).
  * listen(5): Configures a software buffer capable of holding up to 5 concurrent
    inbound connection requests in a queue before dropping subsequent attempts.

Code (Runtime Execution Block):
      while True:
          handle_dns(dns_sock)
          try:
              client, addr = http_sock.accept()
              request = client.recv(1024)
             
              temp, humidity = read_temp()
              response = web_page(temp, humidity)
             
              client.send('HTTP/1.1 200 OK\r\n')
              client.send('Content-Type: text/html\r\n')
              client.send('Connection: close\r\n\r\n')
              client.sendall(response.encode('utf-8'))
              client.close()
          except OSError:
              pass
             
          time.sleep(0.02)

Explanation:
  * while True: The permanent execution engine of your weather station.
  * Shared Time-Slicing: In a single loop iteration, the board rapidly checks if
    any client needs DNS routing direction via `handle_dns(dns_sock)`. It then
    immediately dips into a try block to check if a phone browser is attempting
    to grab the web page using `http_sock.accept()`.

Proper HTTP Structure: When a browser connects, the server constructs a genuine
HTTP packet header sequence containing proper transmission states (200 OK) and
content definitions (text/html). It encodes the clean Unicode text characters into
raw streamable binary formatting (response.encode('utf-8')), fires it down the
pipe, and explicitly disconnects the line via client.close() to free the socket slot. [1]
time.sleep(0.02): A vital 20-millisecond scheduling gap. Without this short delay,
the microcontroller's CPU core would loop at maximum speed with zero pause, causing
the internal silicon junction temp to skyrocket. This chip heating would warp
the environmental read accuracy of your nearby DHT11 sensor!
