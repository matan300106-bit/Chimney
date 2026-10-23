# Pittsburgh Chimney Sweeps — website

Single-file site: `index.html` (HTML, CSS and JS inline; only external request is Google Fonts).
Open it in a browser or upload it as-is to any static host (Netlify, Hostinger, GitHub Pages).

## Replace before launch
Search `index.html` for these placeholders:

| Placeholder | Replace with |
|---|---|
| `(412) 555-0142` and `+14125550142` | Real phone number (display + `tel:` links) |
| `hello@pittsburghchimneysweeps.com` | Real email |
| `PA HIC #PA000000` | PA Home Improvement Contractor number |
| `4.9` / `300+` | Real Google rating and review count |
| Review cards (marked `REPLACE`) | Real Google reviews: name, neighborhood, text |
| `BOOKING_ENDPOINT` (bottom script) | Workiz booking webhook / Formspree URL |
| Hours, service-area chips | Your actual hours and towns |

Until `BOOKING_ENDPOINT` is set, the booking form shows its success screen without sending anything.
