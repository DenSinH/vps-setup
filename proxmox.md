# Setting up proxmox

### Making sure your IP settings are correct
- Check the gateway in `/etc/resolv.conf`, file should contain something like
  ```nameserver 192.168.50.1```
- Check the ip settings in `/etc/network/interfaces`, file should contain something like
  ```
  auto lo
  iface lo inet loopback
  
  iface enp0s25 inet manual
  
  auto vmbr0
  iface vmbr0 inet static
          address 192.168.50.2/24
          gateway 192.168.50.1
          bridge-ports enp0s25
          bridge-stp off
          bridge-fd 0
  
  iface wlp2s0 inet manual
  
  
  source /etc/network/interfaces.d/*
  ```
### Write-heavy services
To save your ssd a litte, it may be worth disabling some write-heavy services and logs:
- I followed the top comment of [this Reddit post](https://www.reddit.com/r/Proxmox/comments/1j4ehgq/is_there_any_way_to_tweak_the_system_to_make_ssds/):
  ```
  systemctl stop pve-ha-crm
  systemctl stop pvesr.timer
  systemctl stop corosync.service
  
  systemctl disable pve-ha-lrm
  systemctl disable pve-ha-crm
  systemctl disable pvesr.timer
  systemctl disable corosync.service
  
  Enable WRITE_TIMEOUT=3600 in `/etc/defaults/rrdcached` config file to reduce disk IOPS.
  
  Disable JOURNAL_PATH=/var/lib/rrdcached/journal/ in `/etc/defaults/rrdcached` config file to reduce disk IOPS. (comment the line)
  
  Added "${FLUSH_TIMEOUT:+-f ${FLUSH_TIMEOUT}} " to /etc/init.d/rrdcached
  ```
  though it seemed `pvesr.timer` did not exist.
- Install [log2ram](https://github.com/azlux/log2ram) and make sure `rsync` is installed (reboot after installing!)

### Power saving stuff
- I enabled power saving mode in my BIOS (F2 on boot for Intel NUCs)

## Setting up Pi-hole
I followed [this tutorial](https://www.naturalborncoder.com/2023/07/installing-pi-hole-on-proxmox/)

## Setting up HA
- Setup VM through [this helper script](https://tteck.github.io/Proxmox/#home-assistant-os-vm)
  - This sets the IP to some DHCP assigned IP at first, you may want to change this through the settings in the VM.
- Pass through Zigbee dongle using [this tutorial](https://smarthomescene.com/guides/how-to-passthrough-usb-devices-to-home-assistant-in-proxmox/)
