import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import EventsPage from "./pages/EventsPage.jsx";
import RegistrationsPage from "./pages/RegistrationsPage.jsx";
import { EVENTS } from "./data/events.js";
import { addRegistration, cancelRegistration } from "./utils/registrations.js";
import { loadRegistrations, saveRegistrations } from "./utils/storage.js";

export default function App() {
  const [registrations, setRegistrations] = useState(loadRegistrations);

  useEffect(() => {
    saveRegistrations(registrations);
  }, [registrations]);

  // Returns the result so the form can show errors or a confirmation.
  function register(event, details) {
    const result = addRegistration(registrations, event, details);
    if (result.ok) setRegistrations(result.registrations);
    return result;
  }

  function cancel(id) {
    setRegistrations((current) => cancelRegistration(current, id));
  }

  return (
    <>
      <Navbar count={registrations.length} />
      <main className="container">
        <Routes>
          <Route path="/" element={<EventsPage events={EVENTS} registrations={registrations} onRegister={register} />} />
          <Route
            path="/registrations"
            element={<RegistrationsPage events={EVENTS} registrations={registrations} onCancel={cancel} />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
