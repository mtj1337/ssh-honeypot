# SSH Honeypot

Falešný SSH server který loguje pokusy o přihlášení a posílá je na Discord.

## Požadavky

```bash
pip install paramiko requests
```

## Nastavení

**1. Vygeneruj SSH klíč**
```bash
ssh-keygen -t rsa -f server.key -N ""
```

**2. Nastav Discord webhook**

V `ssh_honeypot.py` změň:
```python
WEBHOOK_URL = "https://discord.com/api/webhooks/..."
```

Webhook získáš v: Server settings → Integrations → Webhooks → New Webhook → Copy URL

**3. Spusť**
```bash
python ssh_honeypot.py
```

> Port `2222` nevyžaduje root. Pokud chceš port `22`, potřebuješ `sudo`.

## Jak to funguje

- poslouchá na portu `2222`
- každý pokus o přihlášení je odmítnut a zalogován
- každých 60 sekund pošle souhrnnou zprávu na Discord
- pokud přijde jen jeden pokus, pošle ho okamžitě (po uplynutí okna)
