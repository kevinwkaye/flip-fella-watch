# Flip Fella Watch

Flip Fella for the Samsung Galaxy Watch Ultra. Flip clock cards in the middle, a compass bezel that turns with you in real time, battery and steps arcs, two dials and Pebble in a little window at the bottom.

## Get the APK

Every push to `main` builds the face on GitHub Actions and publishes it as a release. Open the [latest release](../../releases/latest) on your phone and download `flip-fella-watch.apk`.

## Install it on the watch

You only need your phone. No PC.

1. On the watch, open **Settings > About watch > Software information** and tap **Software version** seven times to turn on Developer options.
2. Go to **Settings > Developer options**, turn on **ADB debugging** and **Wireless debugging**. Make sure the watch and phone share the same Wi-Fi.
3. In **Wireless debugging**, tap **Pair new device**. Note the pairing code and the IP address and port.
4. On the phone, install **Bugjaeger** from the Play Store, pair with the code and address from step 3, then connect.
5. In Bugjaeger, open the install screen and pick `flip-fella-watch.apk`.
6. On the watch, long press the current face, swipe to the end and add **Flip Fella**.

Later builds install straight over the top, because every build signs with the same key.

## Dials

Long press the face and tap **Customise** to choose what the two dials show. The right dial defaults to steps and also fills the right-hand arc (goal: 10,000). Set the left one to Samsung Health heart rate.

## How it behaves

- The compass reads the watch's rotation sensor only while the screen is awake. With raise to wake, it never runs when the screen is off.
- The minute flips with a staggered split-flap animation.
- Pebble blinks every few seconds.
- Always on display drops to dim outlined cards with no compass.

## Fonts

Roboto Condensed and Saira Condensed, both under the SIL Open Font Licence. Licences are in `licences/`.
