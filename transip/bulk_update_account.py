#!/usr/bin/env python


from transip.service.domain import DomainService
from transip.service.domain import DnsEntry
from dns import resolver
from suds import WebFault

import requests
import argparse


def main():
    """
    Updates all DNS entries in a TransIP account to the value of the IP number of the
    internet connection that is used when calling this script.

    Handy when running a server at home and the ISP has given a new IP number.

    The IP number of 'check-host' is resolved and compared to the current public IP number.
    If they differ, all dns entries that have the 'old' ip number will be updated to 'new'.

    For exanple: ./bulk_update_account.py --check-host check.example.org --user-name example-user

    Warning: this will bulk update all relevant DNS entries in all domains for an account!
    """

    parser = argparse.ArgumentParser()

    parser.add_argument('-u', '--user-name', help='TransIP username', dest='user_name')
    parser.add_argument('-c', '--check-host', help='Check host', dest='check_host')

    parser.add_argument('--dns-server', help='DNS server to use', dest='dns_server')
    parser.add_argument('--api-key', help='TransIP private key', dest='api_key_file')

    args = parser.parse_args()

    if not args.user_name:
        print('Please provide your TransIP username.')
        exit(1)

    if not args.check_host:
        print('Please provide a hostname to be checked for a changed public IP address.')
        exit(1)

    if not args.api_key_file:
        args.api_key_file = 'decrypted_key'

    if not args.dns_server:
        # TransIP DNS server
        args.dns_server = '195.135.195.195'

    domain_service = DomainService(args.user_name, args.api_key_file)

    # Validate that check-host belongs to the account given
    if len([domain_name for domain_name in domain_service.get_domain_names() if
            args.check_host.endswith('.' + domain_name)]) != 1:
        print('The check-host parameter does not match with any of your domain names.')
        exit(1)

    # Find 'old' and 'new' IP number
    res = resolver.Resolver()
    res.nameservers = [args.dns_server]
    old_ip = res.query(args.check_host)[0].address
    current_ip = requests.get('https://api.ipify.org?format=json').json()['ip']

    if old_ip != current_ip:

        print('Old ip: {}, current ip: {}. Updating DNS entries.'.format(old_ip, current_ip))

        for update_domain in domain_service.get_domain_names():

            print('Updating {}'.format(update_domain))

            # Create a new set with entries to be updated
            dns_entries = [DnsEntry(
                entry['name'], entry['expire'], entry['type'],
                current_ip if entry['content'] == old_ip else entry['content']
            ) for entry in domain_service.get_info(update_domain).dnsEntries]

            try:
                result = domain_service.set_dns_entries(update_domain, dns_entries)
                if result is not None:
                    print(result)
            except WebFault as err:
                print(err)
                exit(1)
    else:
        print('Old ip and current ip ({}) are the same. Not updating DNS entries.'.format(old_ip))


if __name__ == '__main__':
    main()
