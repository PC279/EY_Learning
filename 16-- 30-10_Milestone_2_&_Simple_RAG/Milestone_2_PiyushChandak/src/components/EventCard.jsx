import RegistrationForm from "./RegistrationForm.jsx";

export default function EventCard({ event, seatsLeft, isOpen, confirmation, onOpen, onClose, onSubmit }) {
  const full = seatsLeft === 0;
  const taken = event.seats - seatsLeft;
  const [day, month] = event.date.split(" ");

  return (
    <li className="event" data-category={event.category}>
      <div className="event-row">
        <div className="event-date" aria-hidden="true">
          <span className="day">{day}</span>
          <span className="month">{month}</span>
        </div>

        <div className="event-main">
          <p className="category">{event.category}</p>
          <h2>{event.title}</h2>
          <p className="when">
            {event.date} at {event.time}
          </p>
        </div>

        <div className="event-seats">
          <div className="dots" aria-hidden="true">
            {Array.from({ length: event.seats }, (_, i) => (
              <span key={`${event.id}-seat-${i}`} className={i < taken ? "dot taken" : "dot"} />
            ))}
          </div>
          <dl>
            <div>
              <dt>Available seats</dt>
              <dd className={full ? "full" : ""}>{seatsLeft}</dd>
            </div>
            <div>
              <dt>Total seats</dt>
              <dd>{event.seats}</dd>
            </div>
          </dl>
        </div>

        <div className="event-action">
          {!isOpen && (
            <button type="button" className="primary" disabled={full} onClick={onOpen}>
              {full ? "Fully booked" : "Register"}
            </button>
          )}
        </div>
      </div>

      {confirmation && (
        <p className="success" role="status">
          {confirmation}
        </p>
      )}

      {isOpen && <RegistrationForm event={event} onSubmit={onSubmit} onClose={onClose} />}
    </li>
  );
}
