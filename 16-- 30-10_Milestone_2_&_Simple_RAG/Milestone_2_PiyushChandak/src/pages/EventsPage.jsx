import { useState } from "react";
import EventCard from "../components/EventCard.jsx";
import { CATEGORIES } from "../data/events.js";
import { seatsLeft } from "../utils/registrations.js";

export default function EventsPage({ events, registrations, onRegister }) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [openId, setOpenId] = useState(null);
  const [confirmation, setConfirmation] = useState(null); // { eventId, text }

  const query = search.trim().toLowerCase();
  const visible = events.filter(
    (e) => (category === "All" || e.category === category) && e.title.toLowerCase().includes(query)
  );

  function clearFilters() {
    setSearch("");
    setCategory("All");
  }

  function open(id) {
    setOpenId(id);
    setConfirmation(null);
  }

  function submit(event, details) {
    const result = onRegister(event, details);
    if (result.ok) {
      setOpenId(null);
      setConfirmation({ eventId: event.id, text: `Registration confirmed for ${result.registration.name}.` });
    }
    return result;
  }

  return (
    <>
      <h1>Upcoming events</h1>
      <p className="intro">Short sessions on technology, arts and life skills. Pick one and reserve a seat.</p>

      <div className="filters">
        <div className="search-field">
          <label htmlFor="search">Search by title</label>
          <input
            id="search"
            type="search"
            value={search}
            placeholder="For example, finance"
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div>
          <span className="label" id="category-label">
            Category
          </span>
          <div className="chips" role="group" aria-labelledby="category-label">
            {CATEGORIES.map((c) => (
              <button key={c} type="button" aria-pressed={category === c} onClick={() => setCategory(c)}>
                {c}
              </button>
            ))}
          </div>
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="empty">
          <p>No events match your search. Try a different title or choose another category.</p>
          <button type="button" onClick={clearFilters}>
            Clear search and filter
          </button>
        </div>
      ) : (
        <ul className="events">
          {visible.map((event) => (
            <EventCard
              key={event.id}
              event={event}
              seatsLeft={seatsLeft(event, registrations)}
              isOpen={openId === event.id}
              confirmation={confirmation?.eventId === event.id ? confirmation.text : null}
              onOpen={() => open(event.id)}
              onClose={() => setOpenId(null)}
              onSubmit={(details) => submit(event, details)}
            />
          ))}
        </ul>
      )}
    </>
  );
}
