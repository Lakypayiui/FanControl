#  Fan Control for macOS (Intel)

A lightweight, native fan controller for the macOS menu bar, designed specifically for Intel architectures. It allows you to monitor system temperatures and take manual or automatic control of fan RPMs.
###  Preview
<img width="357" height="320" alt="FanControl" src="https://github.com/user-attachments/assets/8adc616c-5c91-4b2c-8635-a8a973f8884e" />


##  Features

* **Real-time monitoring:** Direct reading from the SMC (System Management Controller) for CPU and GPU temperatures.
* **Manual and automatic control:** Intuitive interface to set the RPM of each fan independently or return control to the operating system.
* **Bilingual UI (On-the-fly):** Instantly toggle the interface language between English and Spanish directly from the menu, without reloading the application.
* **Native macOS Integration:** Built entirely with Cocoa/Objective-C APIs (`NSMenu`, `NSView`) for a seamless, native look and feel.
* **Secure privilege escalation:** Uses a *setuid* C binary, allowing hardware modifications without asking for the administrator password every time a fan is adjusted.
 
##  Compatibility and Disclaimer

* **Intel Macs only:** This software interacts with the `AppleSMC` API and the `IOKit` framework, which are specific to Intel architecture. **It is not compatible with Apple Silicon (M1/M2/M3)**.
* **Disclaimer:** Modifying fan speeds can affect your computer's thermal dissipation. Use at your own risk.

##  Installation (End Users)

1. Go to the **Releases** tab of the [repository](https://github.com/Lakypayiui/FanControl) and download the `FanControl-1.0.pkg` file.
2. Double-click the installer. (macOS will ask for your administrator password to configure hardware permissions).
3. Search for **Fan Control** in your Launchpad or Applications folder and run it.
4. A fan icon will appear in your menu bar.

##  Architecture and Development

The project is divided into two main layers to maintain security and performance:

1. **The C Helper (Low level):** Written in pure C using `IOKit`. This compiled binary (`smc-helper`) is the only component that communicates with the hardware. During installation via the `.pkg` package, it is granted root privileges (`chown root:wheel` and `chmod 4755`), acting as a secure bridge.
2. **The Python Interface (High level):** Developed with `rumps` (for the menu bar) and `tkinter` (for the control window). It handles the user logic and invokes the helper transparently.

### Building from Source

If you want to compile the application and generate the installer yourself, you need Python 3, `clang`, and Apple's development tools installed.

```bash
# 1. Clone the repository
git clone [https://github.com/Lakypayiui/FanControl.git](https://github.com/Lakypayiui/FanControl.git)
cd FanControl

# 2. Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run FanControl
python3 src/fan_control_native.py
```
