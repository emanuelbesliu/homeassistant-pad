# PAD Romania - Integrare Home Assistant

Integrare pentru verificarea politelor **PAD** (Polița de Asigurare a Locuinței) din Romania, folosind datele publice de pe **padrom.ro**.

## Functionalitati

- Verificare stare polita PAD (activa/expirata/negasita)
- Senzor data expirare polita
- Senzor zile ramase pana la expirare
- Senzor binar validitate polita (ON/OFF)
- Atribute detaliate: asigurator, adresa, suma asigurata, prima
- Suport serii multiple de polite (RA-002...RX3740)
- Actualizare automata la fiecare 24 ore (configurabil)
- Traduceri complete romana/engleza

## Instalare

### HACS (Recomandat)

1. Deschide HACS in Home Assistant
2. Click pe "Integrations"
3. Click pe meniul cu 3 puncte -> "Custom repositories"
4. Adauga: `https://github.com/emanuelbesliu/homeassistant-pad`
5. Categorie: "Integration"
6. Cauta "PAD Romania" si instaleaza

### Manual

```bash
cd /config/custom_components
git clone https://github.com/emanuelbesliu/homeassistant-pad.git pad
mv pad/custom_components/pad/* pad/
rm -rf pad/custom_components
```

## Configurare

1. Reporniti Home Assistant
2. **Settings -> Devices & Services -> Add Integration**
3. Cautati "PAD Romania"
4. Introduceti: seria politei, numarul politei, CNP/CUI
5. Optional: ajustati intervalul de actualizare din optiunile integrarii

## Senzori

| Senzor | Descriere |
|--------|-----------|
| Policy Status | Starea politei (Active/Expired/Not Found) |
| Policy Expiry | Data de expirare a politei |
| Days Until Expiry | Zile ramase pana la expirare |
| Policy Valid | Senzor binar ON cand polita este valida |

## Support

- [GitHub Issues](https://github.com/emanuelbesliu/homeassistant-pad/issues)
- [Documentatie completa](README.md)
