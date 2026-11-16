import { useState } from "react";
import { EMAIL_MAX, NAME_MAX } from "../utils/registrations.js";

export default function RegistrationForm({ event, onSubmit, onClose }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState({});

  function handleSubmit(e) {
    e.preventDefault();
    const result = onSubmit({ name, email });
    if (!result.ok) setErrors(result.errors);
  }

  return (
    <form className="form" onSubmit={handleSubmit} noValidate aria-label={`Register for ${event.title}`}>
      {errors.form && (
        <p className="error" role="alert">
          {errors.form}
        </p>
      )}

      <div className="field">
        <label htmlFor={`name-${event.id}`}>Full name</label>
        <input
          id={`name-${event.id}`}
          type="text"
          value={name}
          maxLength={NAME_MAX}
          autoComplete="name"
          aria-invalid={Boolean(errors.name)}
          aria-describedby={errors.name ? `name-error-${event.id}` : undefined}
          onChange={(e) => setName(e.target.value)}
        />
        {errors.name && (
          <p className="error" id={`name-error-${event.id}`} role="alert">
            {errors.name}
          </p>
        )}
      </div>

      <div className="field">
        <label htmlFor={`email-${event.id}`}>Email address</label>
        <input
          id={`email-${event.id}`}
          type="email"
          value={email}
          maxLength={EMAIL_MAX}
          autoComplete="email"
          aria-invalid={Boolean(errors.email)}
          aria-describedby={errors.email ? `email-error-${event.id}` : undefined}
          onChange={(e) => setEmail(e.target.value)}
        />
        {errors.email && (
          <p className="error" id={`email-error-${event.id}`} role="alert">
            {errors.email}
          </p>
        )}
      </div>

      <div className="actions">
        <button type="submit" className="primary">
          Confirm registration
        </button>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>
    </form>
  );
}
