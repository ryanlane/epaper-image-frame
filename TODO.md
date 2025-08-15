# TODO: Network Discovery for E-Paper Frames

## mDNS/ZeroConf Discovery
- Implement mDNS/Bonjour/ZeroConf service advertisement for each frame using Python's `zeroconf` library.
- Advertise a custom service (e.g., `_epaperframe._tcp.local`) with device info (name, IP, port).
- On the homepage, scan for all `_epaperframe._tcp.local` services and list discovered frames with links to manage them.
- Ensure each frame advertises its hostname and management URL.
- Test discovery on typical home networks (Windows, Mac, Linux, iOS, Android).
- Optionally, allow manual addition of frames if discovery fails.

## References
- Python zeroconf: https://github.com/jstasiak/python-zeroconf
- mDNS/Bonjour overview: https://en.wikipedia.org/wiki/Multicast_DNS

## Implementation Steps
1. Add `zeroconf` to `requirements.txt`.
2. Add service advertisement to frame startup (FastAPI lifespan or main).
3. Add homepage endpoint to scan for services and display devices.
4. Add UI to link/manage discovered frames.
5. Document troubleshooting for network/firewall issues.
