import { Link } from "react-router-dom";

export default function RegistrationsPage({ events, registrations, onCancel }) {
  function handleCancel(registration, event) {
    if (window.confirm(`Cancel ${registration.name}'s registration for ${event.title}?`)) {
      onCancel(registration.id);
    }
  }

  return (
    <>
      <h1>Registrations</h1>
      <p className="intro">Everyone who is booked in. Cancelling a registration frees the seat straight away.</p>

      {registrations.length === 0 ? (
        <div className="empty">
          <p>There are no registrations yet.</p>
          <Link to="/">Browse events</Link>
        </div>
      ) : (
        <ul className="registrations">
          {registrations.map((r) => {
            const event = events.find((e) => e.id === r.eventId);
            return (
              <li className="reg" key={r.id}>
                <div className="reg-who">
                  <h2>{r.name}</h2>
                  <p>{r.email}</p>
                </div>
                <dl className="reg-what">
                  <div>
                    <dt>Event</dt>
                    <dd>{event.title}</dd>
                  </div>
                  <div>
                    <dt>Date</dt>
                    <dd>{event.date}</dd>
                  </div>
                </dl>
                <div className="reg-action">
                  <button type="button" className="danger" onClick={() => handleCancel(r, event)}>
                    Cancel registration
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
