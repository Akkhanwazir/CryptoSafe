from io import BytesIO
from pathlib import Path
from threading import Lock

from flask import (
    Flask,
    request,
    render_template_string,
    send_file,
    redirect,
    url_for,
    flash,
)
from cryptography.fernet import Fernet, InvalidToken
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = Fernet.generate_key().decode()
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# This demonstration app keeps only the latest encrypted file in memory.
# Restarting the server clears it.
storage_lock = Lock()
latest_encrypted = {
    "data": None,
    "filename": None,
    "key": None,
}


HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CryptoSafe — Secure File Encryption</title>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg: #070b16;
    --panel: rgba(16, 24, 43, .78);
    --panel-solid: #10182b;
    --border: rgba(120, 157, 215, .16);
    --text: #f1f5ff;
    --muted: #8b9ab6;
    --cyan: #4de5f2;
    --blue: #628cff;
    --purple: #a36cff;
    --green: #43e6a5;
    --red: #ff6b83;
    --shadow: 0 25px 80px rgba(0, 0, 0, .25);
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;
    min-height: 100vh;
    background:
        radial-gradient(ellipse at 50% -20%, rgba(42, 92, 190, .22), transparent 55%),
        radial-gradient(ellipse at 100% 45%, rgba(103, 49, 180, .11), transparent 42%),
        var(--bg);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    overflow-x: hidden;
}

body::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: -1;
    opacity: .17;
    background-image:
        linear-gradient(rgba(99, 135, 195, .09) 1px, transparent 1px),
        linear-gradient(90deg, rgba(99, 135, 195, .09) 1px, transparent 1px);
    background-size: 45px 45px;
    mask-image: linear-gradient(to bottom, black, transparent 85%);
}

a {
    color: inherit;
    text-decoration: none;
}

button,
input {
    font: inherit;
}

button {
    cursor: pointer;
}

.container {
    width: min(1160px, calc(100% - 40px));
    margin: auto;
}

/* NAVIGATION */

.navbar {
    height: 78px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(130, 160, 220, .10);
    position: relative;
    z-index: 5;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.brand-icon {
    width: 41px;
    height: 41px;
    border-radius: 13px;
    display: grid;
    place-items: center;
    background: linear-gradient(145deg, rgba(77, 229, 242, .18), rgba(98, 140, 255, .16));
    border: 1px solid rgba(77, 229, 242, .35);
    box-shadow: 0 0 25px rgba(77, 229, 242, .08);
}

.brand-icon svg {
    width: 25px;
    height: 25px;
}

.brand-name {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 21px;
    letter-spacing: -.7px;
}

.brand-name span {
    color: var(--cyan);
}

.nav-right {
    display: flex;
    align-items: center;
    gap: 20px;
}

.status-pill {
    display: flex;
    align-items: center;
    gap: 9px;
    border: 1px solid rgba(67, 230, 165, .20);
    color: #a5f4d2;
    background: rgba(67, 230, 165, .06);
    border-radius: 50px;
    padding: 9px 13px;
    font-size: 11px;
    letter-spacing: .5px;
}

.status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 12px var(--green);
    animation: pulse 2s infinite;
}

.motion-button {
    color: var(--muted);
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 12px;
    transition: .2s;
}

.motion-button:hover {
    color: var(--cyan);
    border-color: rgba(77, 229, 242, .4);
}

/* HERO */

.hero {
    text-align: center;
    padding: 58px 0 15px;
    position: relative;
}

.eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--cyan);
    border: 1px solid rgba(77, 229, 242, .20);
    background: rgba(77, 229, 242, .055);
    padding: 8px 13px;
    border-radius: 30px;
    text-transform: uppercase;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    animation: fadeUp .7s both;
}

.eyebrow svg {
    width: 14px;
    height: 14px;
}

.hero h1 {
    margin: 20px 0 13px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(36px, 5.4vw, 65px);
    line-height: 1.06;
    letter-spacing: -3px;
    font-weight: 700;
    animation: fadeUp .8s .08s both;
}

.hero h1 .gradient {
    background: linear-gradient(95deg, #55e9f1 5%, #78a3ff 48%, #b58aff 90%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

.hero p {
    color: var(--muted);
    max-width: 560px;
    margin: 0 auto;
    line-height: 1.8;
    font-size: 14px;
    animation: fadeUp .8s .15s both;
}

/* ANIMATED SHIELD */

.visual-stage {
    position: relative;
    height: 310px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 5px auto 10px;
    max-width: 700px;
    overflow: hidden;
}

.visual-glow {
    position: absolute;
    width: 240px;
    height: 240px;
    border-radius: 50%;
    background: rgba(48, 144, 255, .17);
    filter: blur(65px);
    animation: glowPulse 4s infinite ease-in-out;
}

.orbit {
    position: absolute;
    border: 1px solid rgba(90, 165, 250, .17);
    border-radius: 50%;
    transform: rotate(-18deg);
}

.orbit.one {
    width: 270px;
    height: 110px;
    animation: orbitSpin 15s linear infinite;
}

.orbit.two {
    width: 350px;
    height: 155px;
    transform: rotate(55deg);
    border-color: rgba(163, 108, 255, .17);
    animation: orbitSpin 21s linear infinite reverse;
}

.orbit.three {
    width: 435px;
    height: 210px;
    transform: rotate(-30deg);
    border-style: dashed;
    border-color: rgba(77, 229, 242, .11);
    animation: orbitSpin 35s linear infinite;
}

.shield-wrap {
    position: relative;
    z-index: 2;
    width: 145px;
    height: 165px;
    display: grid;
    place-items: center;
    filter: drop-shadow(0 0 30px rgba(77, 229, 242, .18));
    animation: float 4s ease-in-out infinite;
}

.shield-svg {
    width: 130px;
    height: 150px;
    overflow: visible;
}

.shield-outline {
    fill: rgba(16, 36, 69, .86);
    stroke: var(--cyan);
    stroke-width: 1.5;
}

.shield-inner {
    fill: url(#shieldGradient);
    opacity: .65;
}

.shield-check {
    fill: none;
    stroke: #d9ffff;
    stroke-width: 4;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: 60;
    stroke-dashoffset: 0;
    animation: checkGlow 3s infinite;
}

.float-icon {
    position: absolute;
    display: grid;
    place-items: center;
    width: 46px;
    height: 46px;
    border: 1px solid rgba(119, 165, 235, .23);
    background: rgba(15, 27, 49, .88);
    border-radius: 15px;
    color: var(--cyan);
    box-shadow: 0 10px 30px rgba(0, 0, 0, .2);
    animation: float 4s ease-in-out infinite;
}

.float-icon svg {
    width: 22px;
    height: 22px;
}

.icon-file {
    top: 50px;
    left: calc(50% - 170px);
    color: #a98cff;
    animation-delay: -.8s;
}

.icon-lock {
    top: 55px;
    right: calc(50% - 165px);
    color: var(--cyan);
    animation-delay: -1.5s;
}

.icon-key {
    bottom: 43px;
    left: calc(50% - 135px);
    color: #81a5ff;
    animation-delay: -2s;
}

.icon-check {
    bottom: 38px;
    right: calc(50% - 145px);
    color: var(--green);
    animation-delay: -1.2s;
}

.visual-label {
    position: absolute;
    bottom: 6px;
    color: #647894;
    text-transform: uppercase;
    font-size: 9px;
    letter-spacing: 2px;
}

/* WORKSPACE */

.workspace {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
    align-items: stretch;
    padding: 15px 0 30px;
}

.card {
    position: relative;
    background: linear-gradient(150deg, rgba(20, 31, 54, .92), rgba(11, 18, 33, .94));
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 24px;
    box-shadow: var(--shadow);
    overflow: hidden;
    transition: border-color .25s, transform .25s, box-shadow .25s;
    animation: fadeUp .7s both;
}

.card:hover {
    border-color: rgba(77, 229, 242, .30);
    box-shadow: 0 22px 65px rgba(0, 0, 0, .25), 0 0 35px rgba(77, 229, 242, .035);
    transform: translateY(-3px);
}

.card::before {
    content: "";
    height: 1px;
    position: absolute;
    top: 0;
    left: 12%;
    right: 12%;
    background: linear-gradient(90deg, transparent, rgba(77, 229, 242, .38), transparent);
}

.card-heading {
    display: flex;
    align-items: center;
    gap: 13px;
    margin-bottom: 22px;
}

.heading-icon {
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    border-radius: 13px;
    flex-shrink: 0;
}

.heading-icon svg {
    width: 21px;
    height: 21px;
}

.heading-icon.encrypt {
    color: var(--cyan);
    background: rgba(77, 229, 242, .10);
    border: 1px solid rgba(77, 229, 242, .18);
}

.heading-icon.decrypt {
    color: #b69aff;
    background: rgba(163, 108, 255, .11);
    border: 1px solid rgba(163, 108, 255, .20);
}

.card-heading h2 {
    margin: 0 0 5px;
    font-size: 16px;
    font-weight: 700;
}

.card-heading p {
    margin: 0;
    color: var(--muted);
    font-size: 11px;
}

.step-label {
    margin-left: auto;
    color: #647894;
    font-size: 10px;
    letter-spacing: 1px;
    align-self: flex-start;
}

/* DROP ZONE */

.drop-zone {
    min-height: 170px;
    border: 1px dashed rgba(117, 155, 216, .32);
    background: rgba(7, 14, 28, .45);
    border-radius: 15px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    text-align: center;
    padding: 20px 12px;
    cursor: pointer;
    transition: .25s;
    position: relative;
}

.drop-zone:hover,
.drop-zone.dragover {
    border-color: var(--cyan);
    background: rgba(77, 229, 242, .055);
    box-shadow: inset 0 0 35px rgba(77, 229, 242, .035);
}

.drop-zone.has-file {
    border-style: solid;
    border-color: rgba(67, 230, 165, .5);
    background: rgba(67, 230, 165, .035);
}

.upload-symbol {
    width: 45px;
    height: 45px;
    display: grid;
    place-items: center;
    border-radius: 14px;
    color: var(--cyan);
    background: rgba(77, 229, 242, .09);
    margin-bottom: 12px;
}

.upload-symbol svg {
    width: 23px;
    height: 23px;
}

.drop-title {
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 7px;
    overflow-wrap: anywhere;
    max-width: 100%;
}

.drop-subtitle {
    color: var(--muted);
    font-size: 10px;
    line-height: 1.7;
}

.browse-text {
    color: var(--cyan);
    font-weight: 600;
}

.file-input {
    display: none;
}

.file-meta {
    margin-top: 9px;
    font-size: 10px;
    color: var(--green);
    min-height: 14px;
    overflow-wrap: anywhere;
}

/* INPUTS AND BUTTONS */

.field-label {
    display: block;
    margin: 19px 0 9px;
    color: #b6c4dc;
    font-size: 11px;
    font-weight: 600;
}

.text-input {
    width: 100%;
    border: 1px solid rgba(120, 157, 215, .22);
    background: rgba(5, 11, 22, .70);
    color: var(--text);
    padding: 13px 14px;
    border-radius: 11px;
    outline: none;
    font-size: 12px;
    transition: border-color .2s, box-shadow .2s;
}

.text-input:focus {
    border-color: rgba(77, 229, 242, .7);
    box-shadow: 0 0 0 3px rgba(77, 229, 242, .07);
}

.text-input::placeholder {
    color: #536580;
}

.primary-button {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    border: 0;
    border-radius: 11px;
    padding: 14px;
    margin-top: 18px;
    color: #07131c;
    background: linear-gradient(100deg, #53e3eb, #71baff);
    font-weight: 800;
    font-size: 12px;
    box-shadow: 0 8px 25px rgba(77, 229, 242, .13);
    transition: transform .2s, box-shadow .2s, filter .2s;
}

.primary-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 30px rgba(77, 229, 242, .23);
    filter: brightness(1.06);
}

.primary-button:active {
    transform: translateY(0);
}

.primary-button:disabled {
    opacity: .6;
    cursor: wait;
}

.primary-button svg {
    width: 17px;
    height: 17px;
}

.decrypt-button {
    background: linear-gradient(100deg, #a18aff, #779fff);
    box-shadow: 0 8px 25px rgba(163, 108, 255, .13);
}

.decrypt-button:hover {
    box-shadow: 0 12px 30px rgba(163, 108, 255, .22);
}

.small-note {
    color: #687b98;
    text-align: center;
    font-size: 10px;
    margin-top: 13px;
    line-height: 1.6;
}

/* RESULT */

.result-card {
    grid-column: 1 / -1;
    padding: 22px 24px;
    animation-delay: .15s;
}

.result-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    flex-wrap: wrap;
}

.result-left {
    display: flex;
    align-items: center;
    gap: 14px;
}

.result-symbol {
    width: 48px;
    height: 48px;
    display: grid;
    place-items: center;
    border: 1px solid rgba(67, 230, 165, .2);
    background: rgba(67, 230, 165, .08);
    color: var(--green);
    border-radius: 14px;
    flex-shrink: 0;
}

.result-symbol svg {
    width: 24px;
    height: 24px;
}

.result-text h3 {
    margin: 0 0 6px;
    font-size: 14px;
}

.result-text p {
    color: var(--muted);
    font-size: 11px;
    margin: 0;
    line-height: 1.7;
}

.result-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.secondary-button {
    border: 1px solid rgba(120, 157, 215, .25);
    background: rgba(255, 255, 255, .025);
    color: #c9d6eb;
    border-radius: 10px;
    padding: 11px 14px;
    font-size: 11px;
    font-weight: 600;
    transition: .2s;
}

.secondary-button:hover {
    border-color: var(--cyan);
    color: var(--cyan);
}

.download-button {
    border-color: rgba(67, 230, 165, .3);
    background: rgba(67, 230, 165, .08);
    color: #8df0c3;
}

.key-box {
    margin-top: 20px;
    padding: 15px;
    background: rgba(5, 11, 22, .75);
    border: 1px solid rgba(67, 230, 165, .2);
    border-radius: 12px;
}

.key-title {
    font-size: 10px;
    color: var(--green);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
    font-weight: 700;
}

.key-row {
    display: flex;
    align-items: center;
    gap: 10px;
}

.key-value {
    flex: 1;
    min-width: 0;
    color: #b8f7df;
    font-family: monospace;
    font-size: 11px;
    overflow-wrap: anywhere;
    line-height: 1.7;
    user-select: all;
}

.key-warning {
    color: #8798b3;
    font-size: 10px;
    margin-top: 11px;
    line-height: 1.7;
}

.empty-result {
    display: flex;
    align-items: center;
    gap: 13px;
}

.empty-circle {
    width: 45px;
    height: 45px;
    display: grid;
    place-items: center;
    color: #7184a3;
    background: rgba(113, 132, 163, .08);
    border: 1px solid rgba(113, 132, 163, .15);
    border-radius: 13px;
}

.empty-circle svg {
    width: 22px;
    height: 22px;
}

.empty-result h3 {
    font-size: 13px;
    margin: 0 0 5px;
    color: #c5d1e6;
}

.empty-result p {
    margin: 0;
    color: #6e819f;
    font-size: 11px;
}

/* SECURITY STRIP */

.security-strip {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin: 0 0 55px;
}

.security-item {
    border: 1px solid rgba(120, 157, 215, .11);
    background: rgba(16, 24, 43, .40);
    border-radius: 13px;
    padding: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.security-icon {
    color: var(--cyan);
    width: 35px;
    height: 35px;
    display: grid;
    place-items: center;
    background: rgba(77, 229, 242, .06);
    border-radius: 10px;
    flex-shrink: 0;
}

.security-icon svg {
    width: 18px;
    height: 18px;
}

.security-item strong {
    display: block;
    font-size: 11px;
    margin-bottom: 5px;
}

.security-item span {
    display: block;
    font-size: 10px;
    color: var(--muted);
    line-height: 1.5;
}

/* MESSAGES */

.flash-container {
    margin: 12px 0 0;
}

.alert {
    padding: 13px 16px;
    border: 1px solid rgba(77, 229, 242, .25);
    border-radius: 12px;
    background: rgba(77, 229, 242, .07);
    color: #bdfaff;
    font-size: 12px;
    line-height: 1.6;
    animation: fadeUp .3s both;
}

.alert.error {
    color: #ffb7c3;
    border-color: rgba(255, 107, 131, .3);
    background: rgba(255, 107, 131, .07);
}

.alert.success {
    color: #a9f5d3;
    border-color: rgba(67, 230, 165, .25);
    background: rgba(67, 230, 165, .06);
}

.footer {
    border-top: 1px solid rgba(130, 160, 220, .10);
    padding: 23px 0 30px;
    display: flex;
    justify-content: space-between;
    gap: 15px;
    flex-wrap: wrap;
    color: #657791;
    font-size: 10px;
}

.footer strong {
    color: #8b9bb6;
}

.toast {
    position: fixed;
    right: 24px;
    bottom: 24px;
    z-index: 50;
    max-width: calc(100vw - 40px);
    padding: 13px 17px;
    background: #13243a;
    border: 1px solid rgba(77, 229, 242, .3);
    border-radius: 12px;
    color: #d9fcff;
    font-size: 12px;
    box-shadow: 0 15px 50px rgba(0, 0, 0, .4);
    opacity: 0;
    transform: translateY(15px);
    pointer-events: none;
    transition: .3s;
}

.toast.show {
    opacity: 1;
    transform: translateY(0);
}

/* ANIMATIONS */

@keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 12px var(--green); }
    50% { opacity: .55; box-shadow: 0 0 3px var(--green); }
}

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(15px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}

@keyframes glowPulse {
    0%, 100% { opacity: .65; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.15); }
}

@keyframes orbitSpin {
    from { rotate: 0deg; }
    to { rotate: 360deg; }
}

@keyframes checkGlow {
    0%, 100% { filter: drop-shadow(0 0 2px rgba(77, 229, 242, .4)); }
    50% { filter: drop-shadow(0 0 9px rgba(77, 229, 242, .9)); }
}

body.motion-off *,
body.motion-off *::before,
body.motion-off *::after {
    animation-play-state: paused !important;
    scroll-behavior: auto !important;
}

/* RESPONSIVE */

@media (max-width: 760px) {
    .container {
        width: min(100% - 28px, 560px);
    }

    .navbar {
        height: 68px;
    }

    .brand-name {
        font-size: 18px;
    }

    .status-pill {
        display: none;
    }

    .hero {
        padding-top: 44px;
    }

    .hero h1 {
        letter-spacing: -1.8px;
    }

    .hero p {
        font-size: 12px;
    }

    .visual-stage {
        height: 270px;
    }

    .orbit.one {
        width: 230px;
    }

    .orbit.two {
        width: 290px;
    }

    .orbit.three {
        width: 340px;
    }

    .icon-file {
        left: calc(50% - 125px);
    }

    .icon-lock {
        right: calc(50% - 125px);
    }

    .icon-key {
        left: calc(50% - 110px);
    }

    .icon-check {
        right: calc(50% - 110px);
    }

    .workspace {
        grid-template-columns: 1fr;
        gap: 15px;
    }

    .result-card {
        grid-column: auto;
    }

    .security-strip {
        grid-template-columns: 1fr;
    }

    .result-content {
        align-items: flex-start;
    }

    .result-actions {
        width: 100%;
    }

    .result-actions form,
    .result-actions button,
    .result-actions a {
        flex: 1;
        text-align: center;
    }

    .key-row {
        align-items: flex-start;
        flex-direction: column;
    }

    .footer {
        flex-direction: column;
    }
}

@media (max-width: 400px) {
    .card {
        padding: 17px;
    }

    .step-label {
        display: none;
    }

    .motion-button {
        padding: 8px;
        font-size: 10px;
    }

    .visual-stage {
        height: 240px;
    }

    .float-icon {
        width: 39px;
        height: 39px;
    }

    .icon-file {
        left: calc(50% - 110px);
    }

    .icon-lock {
        right: calc(50% - 110px);
    }
}
</style>
</head>

<body>

<div class="container">

    <nav class="navbar">
        <a href="{{ url_for('home') }}" class="brand">
            <div class="brand-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="#4de5f2"
                     stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2 20 5v6c0 5-3.5 8.5-8 11-4.5-2.5-8-6-8-11V5z"/>
                    <path d="m9 12 2 2 4-4"/>
                </svg>
            </div>
            <div class="brand-name">Crypto<span>Safe</span></div>
        </a>

        <div class="nav-right">
            <div class="status-pill">
                <span class="status-dot"></span>
                SYSTEM OPERATIONAL
            </div>
            <button class="motion-button" id="motionBtn" type="button">
                ◉ Motion On
            </button>
        </div>
    </nav>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="flash-container">
                {% for category, message in messages %}
                    <div class="alert {{ category }}">{{ message }}</div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}

    <header class="hero">
        <div class="eyebrow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="5" y="10" width="14" height="11" rx="2"/>
                <path d="M8 10V7a4 4 0 0 1 8 0v3"/>
            </svg>
            NEXT-GEN FILE SECURITY
        </div>

        <h1>Your Data. <span class="gradient">Your Control.</span></h1>

        <p>
            Protect your digital world with powerful file encryption.
            Secure your files, keep your keys safe, and regain access
            whenever you need it.
        </p>
    </header>

    <section class="visual-stage" aria-label="Animated security shield">
        <div class="visual-glow"></div>
        <div class="orbit one"></div>
        <div class="orbit two"></div>
        <div class="orbit three"></div>

        <div class="float-icon icon-file">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                <path d="M13 2v7h7M8 14h8M8 18h6"/>
            </svg>
        </div>

        <div class="float-icon icon-lock">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <rect x="4" y="10" width="16" height="11" rx="2"/>
                <path d="M8 10V7a4 4 0 0 1 8 0v3"/>
                <circle cx="12" cy="15" r="1"/>
            </svg>
        </div>

        <div class="float-icon icon-key">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="8" cy="15" r="5"/>
                <path d="m11.5 11.5 8-8 2 2-3 3 2 2-3 3-2-2"/>
            </svg>
        </div>

        <div class="float-icon icon-check">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
                <path d="m5 12 4 4L19 6"/>
            </svg>
        </div>

        <div class="shield-wrap">
            <svg class="shield-svg" viewBox="0 0 120 140">
                <defs>
                    <linearGradient id="shieldGradient" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stop-color="#4de5f2"/>
                        <stop offset="100%" stop-color="#628cff"/>
                    </linearGradient>
                </defs>
                <path class="shield-outline"
                      d="M60 5 108 23v37c0 33-20 56-48 73C32 116 12 93 12 60V23z"/>
                <path class="shield-inner"
                      d="M60 15 98 29v31c0 26-15 45-38 59C37 105 22 86 22 60V29z"/>
                <path class="shield-check" d="m39 68 14 14 30-34"/>
            </svg>
        </div>

        <div class="visual-label">ENCRYPTED · AUTHENTICATED · PROTECTED</div>
    </section>

    <main class="workspace">

        <!-- ENCRYPTION PANEL -->
        <section class="card">
            <div class="card-heading">
                <div class="heading-icon encrypt">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="4" y="10" width="16" height="11" rx="2"/>
                        <path d="M8 10V7a4 4 0 0 1 8 0v3"/>
                    </svg>
                </div>
                <div>
                    <h2>Encrypt File</h2>
                    <p>Lock your file with secure encryption</p>
                </div>
                <span class="step-label">STEP 01</span>
            </div>

            <form action="{{ url_for('encrypt_file') }}"
                  method="POST" enctype="multipart/form-data"
                  class="upload-form" id="encryptForm">

                <label class="drop-zone" id="encryptDrop" for="encryptFile">
                    <div class="upload-symbol">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                             stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 16V4m-5 5 5-5 5 5"/>
                            <path d="M4 16v4h16v-4"/>
                        </svg>
                    </div>
                    <div class="drop-title" id="encryptTitle">
                        Drop your file here
                    </div>
                    <div class="drop-subtitle">
                        or <span class="browse-text">browse files</span><br>
                        Maximum file size: 16 MB
                    </div>
                    <input class="file-input" type="file" id="encryptFile"
                           name="file" required>
                </label>

                <div class="file-meta" id="encryptMeta"></div>

                <button class="primary-button" type="submit">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="4" y="10" width="16" height="11" rx="2"/>
                        <path d="M8 10V7a4 4 0 0 1 8 0v3"/>
                    </svg>
                    Encrypt & Generate Key
                </button>

                <p class="small-note">
                    A unique encryption key will be generated for your file.
                </p>
            </form>
        </section>

        <!-- DECRYPTION PANEL -->
        <section class="card">
            <div class="card-heading">
                <div class="heading-icon decrypt">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="4" y="10" width="16" height="11" rx="2"/>
                        <path d="M8 10V7a4 4 0 0 1 8 0"/>
                        <path d="m10 15 2 2 2-2"/>
                    </svg>
                </div>
                <div>
                    <h2>Decrypt File</h2>
                    <p>Restore your file using its secret key</p>
                </div>
                <span class="step-label">STEP 02</span>
            </div>

            <form action="{{ url_for('decrypt_file') }}"
                  method="POST" enctype="multipart/form-data"
                  class="upload-form" id="decryptForm">

                <label class="drop-zone" id="decryptDrop" for="decryptFile">
                    <div class="upload-symbol">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                             stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 16V4m-5 5 5-5 5 5"/>
                            <path d="M4 16v4h16v-4"/>
                        </svg>
                    </div>
                    <div class="drop-title" id="decryptTitle">
                        Drop encrypted file here
                    </div>
                    <div class="drop-subtitle">
                        or <span class="browse-text">browse files</span><br>
                        Select a file ending in .encrypted
                    </div>
                    <input class="file-input" type="file" id="decryptFile"
                           name="file" required>
                </label>

                <div class="file-meta" id="decryptMeta"></div>

                <label class="field-label" for="keyInput">SECRET DECRYPTION KEY</label>
                <input class="text-input" type="text" id="keyInput" name="key"
                       placeholder="Paste your Fernet key here" required
                       autocomplete="off" spellcheck="false">

                <button class="primary-button decrypt-button" type="submit">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="4" y="10" width="16" height="11" rx="2"/>
                        <path d="M8 10V7a4 4 0 0 1 8 0"/>
                        <path d="m10 15 2 2 2-2"/>
                    </svg>
                    Decrypt & Restore File
                </button>

                <p class="small-note">
                    The correct key is required to recover the original file.
                </p>
            </form>
        </section>

        <!-- RESULT PANEL -->
        <section class="card result-card">
            <div class="card-heading">
                <div class="heading-icon encrypt">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <path d="M14 2v6h6M8 13h8M8 17h8"/>
                    </svg>
                </div>
                <div>
                    <h2>Security Console</h2>
                    <p>Your encryption activity and available downloads</p>
                </div>
                <span class="step-label">ACTIVITY</span>
            </div>

            {% if key %}
                <div class="result-content">
                    <div class="result-left">
                        <div class="result-symbol">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                 stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                <path d="m5 12 4 4L19 6"/>
                            </svg>
                        </div>
                        <div class="result-text">
                            <h3>Encryption Successful</h3>
                            <p>Your file has been encrypted and is ready to download.</p>
                        </div>
                    </div>

                    <div class="result-actions">
                        <a class="secondary-button download-button"
                           href="{{ url_for('download_encrypted') }}">
                            ↓ Download Encrypted File
                        </a>
                    </div>
                </div>

                <div class="key-box">
                    <div class="key-title">Your Secret Encryption Key</div>
                    <div class="key-row">
                        <div class="key-value" id="generatedKey">{{ key }}</div>
                        <button class="secondary-button" type="button"
                                onclick="copyKey('generatedKey')">
                            Copy Key
                        </button>
                    </div>
                    <div class="key-warning">
                        Important: Save this key in a secure location. Without it,
                        you cannot decrypt your file. Do not share it with anyone.
                    </div>
                </div>

            {% elif decrypted %}
                <div class="result-content">
                    <div class="result-left">
                        <div class="result-symbol">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                 stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                <path d="m5 12 4 4L19 6"/>
                            </svg>
                        </div>
                        <div class="result-text">
                            <h3>Decryption Successful</h3>
                            <p>Your original file has been restored.</p>
                        </div>
                    </div>
                    <div class="result-actions">
                        <a class="secondary-button download-button"
                           href="{{ url_for('download_decrypted') }}">
                            ↓ Download Restored File
                        </a>
                    </div>
                </div>

            {% else %}
                <div class="empty-result">
                    <div class="empty-circle">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                             stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="9"/>
                            <path d="M12 11v5M12 7h.01"/>
                        </svg>
                    </div>
                    <div>
                        <h3>Waiting for an operation</h3>
                        <p>Encrypt or decrypt a file to see your results here.</p>
                    </div>
                </div>
            {% endif %}
        </section>

    </main>

    <section class="security-strip">
        <div class="security-item">
            <div class="security-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="4" y="10" width="16" height="11" rx="2"/>
                    <path d="M8 10V7a4 4 0 0 1 8 0v3"/>
                </svg>
            </div>
            <div>
                <strong>Fernet Encryption</strong>
                <span>Authenticated symmetric encryption</span>
            </div>
        </div>

        <div class="security-item">
            <div class="security-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2 20 5v6c0 5-3.5 8.5-8 11-4.5-2.5-8-6-8-11V5z"/>
                    <path d="m9 12 2 2 4-4"/>
                </svg>
            </div>
            <div>
                <strong>Integrity Protection</strong>
                <span>Detects invalid keys and tampered data</span>
            </div>
        </div>

        <div class="security-item">
            <div class="security-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9"/>
                    <path d="M12 7v5l3 2"/>
                </svg>
            </div>
            <div>
                <strong>Simple Workflow</strong>
                <span>Encrypt, download, and restore files</span>
            </div>
        </div>
    </section>

    <footer class="footer">
        <div>© 2026 <strong>CryptoSafe</strong> · Secure File Protection</div>
        <div>Built with Python, Flask & Fernet Cryptography</div>
    </footer>

</div>

<div class="toast" id="toast" role="status" aria-live="polite"></div>

<script>
const motionBtn = document.getElementById("motionBtn");

motionBtn.addEventListener("click", () => {
    document.body.classList.toggle("motion-off");

    const isOff = document.body.classList.contains("motion-off");
    motionBtn.textContent = isOff ? "◉ Motion Off" : "◉ Motion On";

    showToast(isOff ? "Animations paused" : "Animations enabled");
});

function showToast(message) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.classList.add("show");

    clearTimeout(window.toastTimer);
    window.toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 2600);
}

async function copyKey(elementId) {
    const element = document.getElementById(elementId);

    if (!element) return;

    const value = element.textContent.trim();

    try {
        await navigator.clipboard.writeText(value);
        showToast("Encryption key copied to clipboard");
    } catch (error) {
        const range = document.createRange();
        range.selectNodeContents(element);

        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);

        showToast("Key selected. Copy it manually.");
    }
}

function setupDropZone(inputId, zoneId, titleId, metaId, defaultTitle) {
    const input = document.getElementById(inputId);
    const zone = document.getElementById(zoneId);
    const title = document.getElementById(titleId);
    const meta = document.getElementById(metaId);

    if (!input || !zone) return;

    function displayFile(file) {
        if (!file) {
            title.textContent = defaultTitle;
            meta.textContent = "";
            zone.classList.remove("has-file");
            return;
        }

        title.textContent = file.name;
        meta.textContent = formatSize(file.size) + " · Selected";
        zone.classList.add("has-file");
    }

    input.addEventListener("change", () => {
        displayFile(input.files[0]);
    });

    zone.addEventListener("dragover", (event) => {
        event.preventDefault();
        zone.classList.add("dragover");
    });

    zone.addEventListener("dragleave", () => {
        zone.classList.remove("dragover");
    });

    zone.addEventListener("drop", (event) => {
        event.preventDefault();
        zone.classList.remove("dragover");

        const file = event.dataTransfer.files[0];

        if (!file) return;

        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;

        displayFile(file);
    });
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

setupDropZone(
    "encryptFile",
    "encryptDrop",
    "encryptTitle",
    "encryptMeta",
    "Drop your file here"
);

setupDropZone(
    "decryptFile",
    "decryptDrop",
    "decryptTitle",
    "decryptMeta",
    "Drop encrypted file here"
);

function setupSubmit(formId) {
    const form = document.getElementById(formId);

    if (!form) return;

    form.addEventListener("submit", (event) => {
        if (!form.checkValidity()) {
            event.preventDefault();
            form.reportValidity();
            return;
        }

        const button = form.querySelector('button[type="submit"]');

        if (button) {
            button.disabled = true;
            button.textContent = "Processing securely...";
        }
    });
}

setupSubmit("encryptForm");
setupSubmit("decryptForm");

const keyInput = document.getElementById("keyInput");

if (keyInput) {
    keyInput.addEventListener("paste", () => {
        setTimeout(() => {
            keyInput.value = keyInput.value.trim();
        }, 0);
    });
}
</script>

</body>
</html>
"""


def render_page(key=None, decrypted=False, status=200):
    return (
        render_template_string(
            HTML,
            key=key,
            decrypted=decrypted,
        ),
        status,
    )


@app.route("/")
def home():
    return render_page()


@app.route("/encrypt", methods=["POST"])
def encrypt_file():
    uploaded_file = request.files.get("file")

    if not uploaded_file or not uploaded_file.filename:
        flash("Please choose a file before encrypting.", "error")
        return redirect(url_for("home"))

    filename = secure_filename(uploaded_file.filename)

    if not filename:
        flash("The selected filename is invalid.", "error")
        return redirect(url_for("home"))

    file_data = uploaded_file.read()

    if not file_data:
        flash("The selected file is empty.", "error")
        return redirect(url_for("home"))

    try:
        key = Fernet.generate_key()
        encrypted_data = Fernet(key).encrypt(file_data)

        encrypted_filename = filename + ".encrypted"

        with storage_lock:
            latest_encrypted["data"] = encrypted_data
            latest_encrypted["filename"] = encrypted_filename
            latest_encrypted["key"] = key

        return render_page(key=key.decode())

    except Exception:
        app.logger.exception("File encryption failed")
        flash("An unexpected error occurred during encryption.", "error")
        return redirect(url_for("home"))


@app.route("/download-encrypted")
def download_encrypted():
    with storage_lock:
        encrypted_data = latest_encrypted["data"]
        encrypted_filename = latest_encrypted["filename"]

    if encrypted_data is None or encrypted_filename is None:
        flash("No encrypted file is available. Encrypt a file first.", "error")
        return redirect(url_for("home"))

    return send_file(
        BytesIO(encrypted_data),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=encrypted_filename,
        max_age=0,
    )


@app.route("/decrypt", methods=["POST"])
def decrypt_file():
    uploaded_file = request.files.get("file")
    key_text = request.form.get("key", "").strip()

    if not uploaded_file or not uploaded_file.filename:
        flash("Please select the encrypted file you want to decrypt.", "error")
        return redirect(url_for("home"))

    if not key_text:
        flash("Please enter the secret encryption key.", "error")
        return redirect(url_for("home"))

    encrypted_data = uploaded_file.read()

    if not encrypted_data:
        flash("The selected encrypted file is empty.", "error")
        return redirect(url_for("home"))

    try:
        key = key_text.encode("ascii")
        cipher = Fernet(key)
        decrypted_data = cipher.decrypt(encrypted_data)

    except (ValueError, UnicodeEncodeError):
        flash("The encryption key format is invalid.", "error")
        return redirect(url_for("home"))

    except InvalidToken:
        flash(
            "Decryption failed. Check your key and make sure the file "
            "has not been modified or corrupted.",
            "error",
        )
        return redirect(url_for("home"))

    except Exception:
        app.logger.exception("File decryption failed")
        flash("An unexpected error occurred during decryption.", "error")
        return redirect(url_for("home"))

    original_filename = secure_filename(uploaded_file.filename)

    if original_filename.lower().endswith(".encrypted"):
        original_filename = original_filename[:-10]

    if not original_filename:
        original_filename = "restored_file"

    # Keep the decrypted file in the current process for the download route.
    # A later decryption replaces the previous result.
    app.config["_LAST_DECRYPTED_DATA"] = decrypted_data
    app.config["_LAST_DECRYPTED_NAME"] = original_filename

    return render_template_string(
        HTML,
        key=None,
        decrypted=True,
    )


@app.route("/download-decrypted")
def download_decrypted():
    decrypted_data = app.config.get("_LAST_DECRYPTED_DATA")
    original_filename = app.config.get(
        "_LAST_DECRYPTED_NAME",
        "restored_file",
    )

    if decrypted_data is None:
        flash("No restored file is available. Decrypt a file first.", "error")
        return redirect(url_for("home"))

    return send_file(
        BytesIO(decrypted_data),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=original_filename,
        max_age=0,
    )


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    flash("The file is too large. The maximum allowed size is 16 MB.", "error")
    return redirect(url_for("home")), 413


if __name__ == "__main__":
    app.run(debug=True)