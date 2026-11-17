# Server setup (Debian VM `youtubesuite`)

## 1. Make the share mount reliably
Put the credentials in a root-only file instead of /etc/fstab:

    sudo sh -c 'printf "username=andru\npassword=YOUR_PASSWORD\n" > /root/.smbcreds && chmod 600 /root/.smbcreds'

Then replace the UBERVAULT line in /etc/fstab with:

    //192.168.1.102/UBERVAULT /mnt/UBERVAULT cifs credentials=/root/.smbcreds,uid=1000,gid=1000,_netdev,nofail,x-systemd.automount,x-systemd.requires=network-online.target 0 0

    sudo systemctl daemon-reload && sudo mount -a

## 2. Install the daily run

    sudo cp deploy/youtube-suite.service deploy/youtube-suite.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now youtube-suite.timer

Run one pass now: `sudo systemctl start youtube-suite.service`
Watch it:         `journalctl -u youtube-suite.service -f`
