# ADS-B SDR Gain Configuration Guidelines (1090 MHz & 978 MHz)

Version: 1.0  
Audience: ADS-B node operators, public safety aggregators, SDR deployers  
Scope: RTL-SDR class hardware (FlightAware ProStick, RTL2832U, Airspy, etc.)

---

## 1. Purpose

This document defines best practices for configuring SDR gain settings for ADS-B reception on:

- **1090 MHz (Mode S / ADS-B ES)**
- **978 MHz (UAT)**

Proper gain configuration maximizes:

- Aircraft detection range  
- Message reliability  
- Decoder stability  
- Network data quality  

---

## 2. Technical Background

SDR gain controls the amount of RF amplification applied before analog-to-digital conversion.

Incorrect gain settings cause:

- **Too low** → missed weak aircraft
- **Too high** → front-end overload, intermodulation, dropped packets, false targets

Gain must be tuned to balance:

- Sensitivity  
- Dynamic range  
- Noise floor  

---

## 3. Frequency Band Characteristics

| Parameter | 1090 MHz ADS-B | 978 MHz UAT |
|----------|----------------|-------------|
| Transmit power | Lower | Higher |
| Aircraft density | High | Moderate |
| Channel congestion | Heavy (urban) | Light |
| Typical noise | Higher | Lower |
| Gain required | Lower | Higher |

**Operational impact:**

- 1090 MHz requires **less gain**
- 978 MHz requires **more gain**

---

## 4. Automatic Gain Control (AGC)

### 4.1 Limitations

AGC dynamically changes gain based on recent signal levels.  
This performs poorly for ADS-B because signals are:

- Short
- Bursty
- Highly variable in strength

Observed issues:

- Missed weak aircraft after strong ones
- Decoder instability
- Reduced message rate
- Oscillating noise floor

---

### 4.2 Recommendation

| Deployment type | Gain mode |
|-----------------|-----------|
| Permanent station | **Manual** |
| Aggregation network | **Manual** |
| Public safety infrastructure | **Manual** |
| Initial hardware testing | AGC acceptable |
| Temporary deployments | AGC acceptable |

---

## 5. Manual Gain Recommendations

### 5.1 Without external LNA

#### Urban / RF-dense environment

| Band | Gain |
|------|------|
| 1090 MHz | 25–35 dB |
| 978 MHz | 35–45 dB |

#### Suburban / rural

| Band | Gain |
|------|------|
| 1090 MHz | 35–45 dB |
| 978 MHz | 42–49 dB |

---

### 5.2 With external LNA (ProStick Plus, mast LNA, etc.)

Reduce values by **10–20 dB**

| Band | Typical range |
|------|--------------|
| 1090 MHz | 24–30 dB |
| 978 MHz | 32–38 dB |

---

## 6. Dual-SDR Deployments (1090 + 978)

Use **separate SDRs** and **separate gain values**.

Example:

```
1090 MHz SDR: 32 dB
978 MHz SDR: 44 dB
```

---

## 7. Gain Tuning Procedure

### Step 1 – Disable AGC

In dump1090/readsb:

```
--gain <value>
```

Notes:
- `-10` often enables AGC
- Manual values range ~0–49.6 dB depending on hardware

---

### Step 2 – Monitor performance metrics

Use web UI statistics:

- Messages / second
- Aircraft count
- Strong signal percentage
- CRC / decode errors
- MLAT sync status

---

### Step 3 – Adjust incrementally

1. Start low  
2. Increase gain in 2–3 dB steps  
3. Observe metrics for 2–5 minutes each step  

Stop increasing when:

- Messages/sec stops improving
- CRC errors rise
- Strong signal % spikes
- False targets appear

Then reduce gain by 2–3 dB.

---

## 8. Environmental Factors Affecting Gain

### Increase gain when:

- Long coax cable runs
- No LNA
- Indoor antenna
- Rural deployment
- 978 MHz operation

### Decrease gain when:

- External LNA present
- Nearby airports
- Cell towers or paging transmitters nearby
- Metal roofs or industrial RF noise
- Dense urban locations

---

## 9. Maximum Gain Mode

Some software supports:

```
--gain max
```

or

```
--gain 49.6
```

Only recommended when:

- Using filtered LNA
- Low RF congestion
- Verified stable performance

Otherwise likely to overload.

---

## 10. Public Safety Aggregation Best Practices

- Enforce **manual gain configuration**
- Document gain values per node
- Avoid AGC on network feeders
- Periodically audit message rate and CRC error levels
- Maintain separate tuning for 1090 and 978 receivers

---

## 11. Reference Default Configuration

### Without LNA

```
1090 MHz: 34 dB
978 MHz: 44 dB
```

### With LNA

```
1090 MHz: 26 dB
978 MHz: 35 dB
```

---

## 12. Revision History

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2026-01 | Initial release |

---
