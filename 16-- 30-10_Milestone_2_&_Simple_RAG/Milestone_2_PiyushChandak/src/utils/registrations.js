export const NAME_MAX = 80;
export const EMAIL_MAX = 254;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function normalizeEmail(email) {
  return email.trim().toLowerCase();
}

function isValidEmail(email) {
  // Length check runs first so the pattern never sees a huge string.
  return email.length <= EMAIL_MAX && EMAIL_PATTERN.test(email);
}

export function seatsLeft(event, registrations) {
  const taken = registrations.filter((r) => r.eventId === event.id).length;
  return Math.max(0, event.seats - taken);
}

export function validateRegistration({ name, email }) {
  const errors = {};
  const cleanName = name.trim();
  const cleanEmail = email.trim();

  if (!cleanName) errors.name = "Please enter your full name.";
  else if (cleanName.length > NAME_MAX) errors.name = `Name must be ${NAME_MAX} characters or fewer.`;

  if (!cleanEmail) errors.email = "Please enter your email address.";
  else if (!isValidEmail(cleanEmail)) errors.email = "Please enter a valid email, for example name@example.com.";

  return errors;
}

function makeId() {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
}

export function addRegistration(registrations, event, { name, email }) {
  const errors = validateRegistration({ name, email });
  if (Object.keys(errors).length > 0) return { ok: false, errors };

  if (seatsLeft(event, registrations) === 0) {
    return { ok: false, errors: { form: "This event is fully booked." } };
  }

  const key = normalizeEmail(email);
  const alreadyIn = registrations.some((r) => r.eventId === event.id && normalizeEmail(r.email) === key);
  if (alreadyIn) {
    return { ok: false, errors: { email: "This email is already registered for this event." } };
  }

  const registration = { id: makeId(), eventId: event.id, name: name.trim(), email: email.trim() };
  return { ok: true, registration, registrations: [...registrations, registration] };
}

export function cancelRegistration(registrations, id) {
  return registrations.filter((r) => r.id !== id);
}

// Stored data can be edited by anyone with dev tools, so rebuild it from scratch
// and keep only entries that obey the same rules as a fresh registration.
export function sanitizeStored(raw, events) {
  if (!Array.isArray(raw)) return [];

  const seenIds = new Set();
  const clean = [];

  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const { id, eventId, name, email } = item;
    if (![id, eventId, name, email].every((v) => typeof v === "string")) continue;

    const event = events.find((e) => e.id === eventId);
    if (!event || !id || id.length > 64 || seenIds.has(id)) continue;
    if (Object.keys(validateRegistration({ name, email })).length > 0) continue;

    const candidate = { id, eventId, name: name.trim(), email: email.trim() };
    const duplicate = clean.some((r) => r.eventId === eventId && normalizeEmail(r.email) === normalizeEmail(email));
    if (duplicate || seatsLeft(event, clean) === 0) continue;

    seenIds.add(id);
    clean.push(candidate);
  }
  return clean;
}
