#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
#
# linksys.py -- program settings on a Linkys router
#
# This tool is designed to help you recover from the occasional episodes
# of catatonia that afflict Linksys boxes. It allows you to batch-program
# them rather than manually entering values to the Web interface.  Commands
# are taken from the command line first, then standard input.
#
# The somewhat spotty coverage of status queries is because I only did the
# ones that were either (a) easy, or (b) necessary.  If you want to know the
# status of the box, look at the web interface.
#
# This code has been tested against the following hardware:
#
#	Hardware  	Firmware
#	----------	---------------------
#	BEFW11S4v2	1.44.2.1, Dec 20 2002
#
# The code is, of course, sensitive to changes in the names of CGI pages
# and field names.
#
# Note: to make the no-arguments form work, you'll need to have the following
# entry in your ~/.netrc file.  If you have changed the router IP address or
# name/password, modify accordingly.
#
# machine 192.168.1.1
#	login ""
#	password admin
#
# By Eric S. Raymond, August April 2003.  All rites reversed.

import sys, re, copy, pycurl, exceptions

class LinksysError(exceptions.Exception):
    def __init__(self, *args):
        self.args = args

class LinksysSession:
    months = 'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec'

    WAN_CONNECT_AUTO = '1'
    WAN_CONNECT_STATIC = '2'
    WAN_CONNECT_PPOE = '3'
    WAN_CONNECT_RAS = '4'
    WAN_CONNECT_PPTP = '5'
    WAN_CONNECT_HEARTBEAT = '6'

    # Substrings to check for on each page load.
    # This may enable us to detect when a firmware change has hosed us.
    check_strings = {
        "" : "basic setup functions"
        }

    def __init__(self):
        self.actions = []
        self.host = "http://192.168.1.1"
        self.verbosity = False
        self.pagecache = {}

    def set_verbosity(self, flag):
        self.verbosity = flag

    # This is not a performance hack -- we need the page cache to do
    # sanity checks at configure time.
    def cache_load(self, page):
        if page not in self.pagecache:
            fetch = pycurl.CGIClient(self.host)
            fetch.set_verbosity(self.verbosity)
            fetch.get(page)
            #print "Response:", fetch.response
            self.pagecache[page] = fetch.response
            if fetch.response.find("401") > -1:
                raise LinksysError("authorization failure.", True)
            elif fetch.response.find(LinksysSession.check_strings[page]) == -1:
                del self.pagecache[page]
                raise LinksysError("check string for page %s missing!" % os.path.join(self.host, page), False)
            fetch.close()
    def cache_flush(self):
        self.pagecache = {}

    # Primitives
    def screen_scrape(self, page, template):
        self.cache_load(page)
        match = re.compile(template).search(self.pagecache[page])
        if match:
            result = match.group(1)
        else:
            result = None
        return result
    def get_MAC_address(self, page, prefix):
        return self.screen_scrape("", prefix+r":[^M]*\(MAC Address: *([^)]*)")
    def set_flag(page, form, flag, value):
        if value:
            self.actions.append(page, form, flag, "1")
        else:
            self.actions.append(page, form, flag, "0")
    def set_IP_address(self, page, cgi, role, ip):
        ind = 0
        for octet in ip.split("."):
            self.actions.append(("", "F1", role + `ind+1`, octet))
            ind += 1

    # Scrape configuration data off the main page
    def get_firmware_version(self):
        # This is fragile.  There is no distinguishing tag before the firmware
        # version, so we have to key off the pattern of the version number.
        # Our model is ">1.44.2.1, Dec 20 2002<"
        return self.screen_scrape("", ">([0-9.v]*, (" + \
                                  LinksysSession.months + ")[^<]*)<", )
    def get_LAN_MAC(self):
        return self.get_MAC_address("", r"LAN IP Address")
    def get_Wireless_MAC(self):
        return self.get_MAC_address("", r"Wireless")
    def get_WAN_MAC(self):
        return self.get_MAC_address("", r"WAN Connection Type")

    # Set configuration data on the main page 
    def set_host_name(self, name):
        self.actions.append(("", "Gozila.cgi", "hostName", name))
    def set_domain_name(self, name):
        self.actions.append(("", "Gozila.cgi", "DomainName", name))
    def set_LAN_IP(self, ip):
        self.set_IP_address("", "Gozila.cgi", "ipAddr", ip)
    def set_LAN_netmask(self, ip):
        if not ip.startswith("255.255.255."):
            raise ValueError
        lastquad = ip.split(".")[-1]
        if lastquad not in ("0", "128", "192", "240", "252"):
            raise ValueError
        self.actions.append("", "Gozila.cgi", "netMask", lastquad)
    def set_wireless(self, flag):
        self.set_flag("", "Gozila.cgi", "wirelessStatus")
    def set_SSID(self, ssid):
        self.actions.append(("", "Gozila.cgi", "wirelessESSID", ssid))
    def set_SSID_broadcast(self, flag):
        self.set_flag("", "Gozila.cgi", "broadcastSSID")
    def set_channel(self, channel):
        self.actions.append(("", "Gozila.cgi", "wirelessChannel", channel))
    def set_WEP(self, flag):
        self.set_flag("", "Gozila.cgi", "WepType")
    # FIXME: Add support for setting WEP keys
    def set_connection_type(self, type):
        self.actions.append(("", "Gozila.cgi", "WANConnectionType", type))
    def set_WAN_IP(self, ip):
        self.set_IP_address("", "Gozila.cgi", "aliasIP", ip)
    def set_WAN_netmask(self, ip):
        self.set_IP_address("", "Gozila.cgi", "aliasMaskIP", ip)
    def set_WAN_gateway_address(self, ip):
        self.set_IP_address("", "Gozila.cgi", "routerIP", ip)
    def set_DNS_server(self, index, dns1):
        self.set_IP_address("", "Gozila.cgi", "dns" + "ABC"[index], ip)

    # Set configuration data on the password page
    def set_password(self, str):
        self.actions.append("Passwd.htm","Gozila.cgi", "sysPasswd", str)
        self.actions.append("Passwd.htm","Gozila.cgi", "sysPasswdConfirm", str)
    def set_UPnP(self, flag):
        self.set_flag("Passwd.htm", "Gozila.cgi", "UPnP_Work")
    def reset(self):
        self.actions,append("Passwd.htm", "Gozila.cgi", "FactoryDefaults")

    def configure(self):
        "Write configuration changes to the Linksys."
        if self.actions:
            ship = {}
            self.cache_flush()
            for (page, cgi, field, value) in self.actions:
                self.cache_load(page)
                if self.pagecache[page].find(field) == -1:
                    print >>sys.stderr, "linksys: field %s not found where expected in page %s!" % (field, os.path.join(self.host, page))
                    continue
                else:
                    if cgi not in ship:
                        ship[cgi] = []
                    ship[cgi].append((field, value))
            # Clearing the action list before shipping is deliberate.
            # Otherwise we could get permanently wedged by a 401.
            self.actions = []
            for (cgi, fields) in ship.items():
                transaction = pycurl.CGIClient(self.host)
                transaction.set_verbosity(self.verbosity)
                transaction.get(cgi, tuple(fields))
                transaction.close()

if __name__ == "__main__":
    import os, cmd

    class LinksysInterpreter(cmd.Cmd):
        """Interpret commands to perform LinkSys programming actions."""
        def __init__(self):
            self.session = LinksysSession()
            if os.isatty(0):
                import readline
                print "Type ? or `help' for help."
                self.prompt = self.session.host + ": "
            else:
                self.prompt = ""
                print "Bar1"

        def flag_command(self, func):
            if line.strip() in ("on", "enable", "yes"):
                func(True)
            elif line.strip() in ("off", "disable", "no"):
                func(False)
            else:
                print >>sys.stderr, "linksys: unknown switch value"
            return 0

        def do_connect(self, line):
            newhost = line.strip()
            if newhost:
                self.session.host = newhost
                self.session.cache_flush()
                self.prompt = self.session.host + ": "
            else:
                print self.session.host
            return 0
        def help_connect(self):
            print "Usage: connect [<hostname-or-IP>]"
            print "Connect to a Linksys by name or IP address."
            print "If no argument is given, print the current host."

        def do_status(self, line):
            self.session.cache_load("")
            if "" in self.session.pagecache:
                print "Firmware:", self.session.get_firmware_version()
                print "LAN MAC:", self.session.get_LAN_MAC()
                print "Wireless MAC:", self.session.get_Wireless_MAC()
                print "WAN MAC:", self.session.get_WAN_MAC()
                print "."
            return 0
        def help_status(self):
            print "Usage: status"
            print "The status command shows the status of the Linksys."
            print "It is mainly useful as a sanity check to make sure"
            print "the box is responding correctly."

        def do_verbose(self, line):
            self.flag_command(self.session.set_verbosity)
        def help_verbose(self):
            print "Usage: verbose {on|off|enable|disable|yes|no}"
            print "Enables display of HTTP requests."

        def do_host(self, line):
            self.session.set_host_name(line)
            return 0
        def help_host(self):
            print "Usage: host <hostname>"
            print "Sets the Host field to be queried by the ISP."

        def do_domain(self, line):
            print "Usage: host <domainname>"
            self.session.set_domain_name(line)
            return 0
        def help_domain(self):
            print "Sets the Domain field to be queried by the ISP."

        def do_lan_address(self, line):
            self.session.set_LAN_IP(line)
            return 0
        def help_lan_address(self):
            print "Usage: lan_address <ip-address>"
            print "Sets the LAN IP address."

        def do_lan_netmask(self, line):
            self.session.set_LAN_netmask(line)
            return 0
        def help_lan_netmask(self):
            print "Usage: lan_netmask <ip-mask>"
            print "Sets the LAN subnetwork mask."

        def do_wireless(self, line):
            self.flag_command(self.session.set_wireless)
            return 0
        def help_wireless(self):
            print "Usage: wireless {on|off|enable|disable|yes|no}"
            print "Switch to enable or disable wireless features."

        def do_ssid(self, line):
            self.session.set_SSID(line)
            return 0
        def help_ssid(self):
            print "Usage: ssid <string>"
            print "Sets the SSID used to control wireless access."

        def do_ssid_broadcast(self, line):
            self.flag_command(self.session.set_SSID_broadcast)
            return 0
        def help_ssid_broadcast(self):
            print "Usage: ssid_broadcast {on|off|enable|disable|yes|no}"
            print "Switch to enable or disable SSID broadcast."

        def do_channel(self, line):
            self.session.set_channel(line)
            return 0
        def help_channel(self):
            print "Usage: channel <number>"
            print "Sets the wireless channel."

        def do_wep(self, line):
            self.flag_command(self.session.set_WEP)
            return 0
        def help_wep(self):
            print "Usage: wep {on|off|enable|disable|yes|no}"
            print "Switch to enable or disable WEP security."

        def do_wan_type(self, line):
            try:
                type=eval("LinksysSession.WAN_CONNECT_"+line.strip().upper())
                self.session.set_connection_type(type)
            except ValueError:
                print >>sys.stderr, "linksys: unknown connection type."
            return 0
        def help_wan_type(self):
            print "Usage: wan_type {auto|static|ppoe|ras|pptp|heartbeat}"
            print "Set the WAN connection type."

        def do_wan_address(self, line):
            self.session.set_WAN_IP(line)
            return 0
        def help_wan_address(self):
            print "Usage: wan_address <ip-address>"
            print "Sets the WAN IP address."

        def do_wan_netmask(self, line):
            self.session.set_WAN_netmask(line)
            return 0
        def help_wan_netmask(self):
            print "Usage: wan_netmask <ip-mask>"
            print "Sets the WAN subnetwork mask."

        def do_wan_gateway(self, line):
            self.session.set_WAN_gateway(line)
            return 0
        def help_wan_gateway(self):
            print "Usage: wan_gateway <ip-address>"
            print "Sets the LAN subnetwork mask."

        def do_dns(self, line):
            (index, address) = line.split()
            if index in ("1", "2", "3"):
                self.session.set_DNS_server(eval(index), address)
            else:
                print >>sys.stderr, "linksys: server index out of bounds."
            return 0
        def help_dns(self):
            print "Usage: dns {1|2|3} <ip-mask>"
            print "Sets a primary, secondary, or tertiary DNS server address."

        def do_password(self, line):
            self.session.set_password(line)
            return 0
        def help_password(self):
            print "Usage: password <string>"
            print "Sets the router password."

        def do_upnp(self, line):
            self.flag_command(self.session.set_UPnP)
            return 0
        def help_upnp(self):
            print "Usage: upnp {on|off|enable|disable|yes|no}"
            print "Switch to enable or disable Universal Plug and Play."

        def do_reset(self):
            self.session.reset()
        def help_reset(self):
            print "Usage: reset"
            print "Reset Linksys settings to factory defaults."

        def do_configure(self, line):
            self.session.configure()
            return 0
        def help_configure(self):
            print "Usage: configure"
            print "Writes the configuration to the Linksys."

        def do_cache(self, line):
            print self.session.pagecache
        def help_cache(self):
            print "Usage: cache"
            print "Display the page cache."

        def do_quit(self, line):
            return 1
        def help_quit(self, line):
            print "The quit command ends your linksys session without"
            print "writing configuration changes to the Linksys."
        def do_EOF(self, line):
            print ""
            self.session.configure()
            return 1
        def help_EOF(self):
            print "The EOF command writes the configuration to the linksys"
            print "and ends your session."

        def default(self, line):
            """Pass the command through to be executed by the shell."""
            os.system(line)
            return 0

        def help_help(self):
            print "On-line help is available through this command."
            print "? is a convenience alias for help."

        def help_introduction(self):
            print """\

This program supports changing the settings on Linksys blue-box routers.  This
capability may come in handy when they freeze up and have to be reset.  Though
it can be used interactively (and will command-prompt when standard input is a
terminal) it is really designed to be used in batch mode. Commands are taken
from the command line first, then standard input.

By default, it is assumed that the Linksys is at http://192.168.1.1, the
default LAN address.  You can connect to a different address or IP with the
'connect' command.  Note that your .netrc must contain correct user/password
credentials for the router.  The entry corresponding to the defaults is:

machine 192.168.1.1
	login ""
	password admin

Most commands queue up changes but don't actually send them to the Linksys.
You can force pending changes to be written with 'configure'.  Otherwise, they
will be shipped to the Linksys at the end of session (e.g.  when the program
running in batch mode encounters end-of-file or you type a control-D).  If you
end the session with `quit', pending changes will be discarded.

For more help, read the topics 'wan', 'lan', and 'wireless'."""

        def help_lan(self):
            print """\
The `lan_address' and `lan_netmask' commands let you set the IP location of
the Linksys on your LAN, or inside.  Normally you'll want to leave these
untouched."""

        def help_wan(self):
            print """\
The WAN commands become significant if you are using the BEFSR41 or any of
the other Linksys boxes designed as DSL or cable-modem gateways.  You will
need to use `wan_type' to declare how you expect to get your address. 

If your ISP has issued you a static address, you'll need to use the
`wan_address', `wan_netmask', and `wan_gateway' commands to set the address
of the router as seen from the WAN, the outside. In this case you will also
need to use the `dns' command to declare which remote servers your DNS
requests should be forwarded to.

Some ISPs may require you to set host and domain for use with dynamic-address
allocation."""

        def help_wireless(self):
            print """\
The channel, ssid, ssid_broadcast, wep, and wireless commands control
wireless routing."""

        def help_switches(self):
            print "Switches may be turned on with 'on', 'enable', or 'yes'."
            print "Switches may be turned off with 'off', 'disable', or 'no'."
            print "Switch commands include: wireless, ssid_broadcast."

        def help_addresses(self):
            print "An address argument must be a valid IP address;"
            print "four decimal numbers separated by dots, each "
            print "between 0 and 255."

        def emptyline(self):
            pass

    interpreter = LinksysInterpreter()
    for arg in sys.argv[1:]:
        interpreter.onecmd(arg)
    fatal = False
    while not fatal:
        try:
            interpreter.cmdloop()
            fatal = True
        except LinksysError, (message, fatal):
            print "linksys:", message

# The following sets edit modes for GNU EMACS
# Local Variables:
# mode:python
# End:
