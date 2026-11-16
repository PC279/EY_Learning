# Event Enrollment Manager

A small React app for a community learning centre. Visitors can browse six upcoming events, register for a seat, see who is registered, and cancel a registration. It is a frontend only project. Registrations are kept in the browser using localStorage, so there is no backend, login or external API.

## What you need

Node.js 20.19 or newer (22.12 or newer also works) and npm. You can check with:

```
node -v
npm -v
```

## Install and run

Open a terminal in the project folder and run:

```
npm install
npm run dev
```

Vite prints a local address, usually http://localhost:5173. Open it in a browser.

## Other commands

```
npm test
npm run build
npm run preview
```

`npm test` runs the logic tests using the test runner that ships with Node, so it needs no extra packages. `npm run build` creates a production build in the `dist` folder, and `npm run preview` serves that build locally.

## How the app works

There are two pages, Events and Registrations, switched with React Router.

On the Events page you can search by title (letter case is ignored) and filter by category with the buttons under the search box. Each card shows the title, category, date, time, total seats and seats still available. Pressing Register opens a form inside that card. The name and email are both required, and the email must look like a real address. A confirmation appears after a successful registration and the seat count drops straight away.

A registration is refused when the event is full or when the same email is already registered for that event. Spaces around the email are ignored and letters are compared without case. The same email can still register for other events. Full events show a disabled "Fully booked" button.

The Registrations page lists every registration with the attendee name, email, event title and event date. Cancel asks for confirmation, removes the registration and gives the seat back.

## Seats and storage

Only registrations are saved, under the localStorage key `eventEnrollmentRegistrations`. Seats available are never stored. They are worked out each time as the event capacity minus the registrations for that event, so the numbers stay correct after a refresh and a cancelled registration never holds a seat.

When the app starts, saved data is checked before it is used. Entries with the wrong shape, an unknown event, a bad email, a repeated email for the same event, or more people than the event has seats are dropped. This stops edited or damaged storage from crashing the page or overbooking an event.

To start again from zero, clear the site data in your browser, or run `localStorage.clear()` in the browser console.

## Folder layout

```
src/
  main.jsx                  entry point and router
  App.jsx                   holds registrations, saves them, defines routes
  styles.css                all styling
  data/events.js            the six starter events and the category list
  utils/registrations.js    validation and seat rules (plain functions)
  utils/registrations.test.js
  utils/storage.js          reading and writing localStorage
  components/Navbar.jsx
  components/EventCard.jsx
  components/RegistrationForm.jsx
  pages/EventsPage.jsx
  pages/RegistrationsPage.jsx
```

The rules for validation, seats, duplicates and cancelling live in `utils/registrations.js` and never touch the browser, which is why they can be tested directly with Node.

## Notes

Dates and times are shown exactly as supplied in the starter data. The look relies on system fonts only, with no images or icon packs, so the app also works offline. No dependencies beyond React, React DOM, React Router and Vite were added. User text is always rendered through JSX, which escapes it, and the code does not use `dangerouslySetInnerHTML`, `eval` or any network request.
