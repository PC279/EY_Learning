import { EVENTS } from "../data/events.js";
import { sanitizeStored } from "./registrations.js";

const KEY = "eventEnrollmentRegistrations";

export function loadRegistrations() {
  try {
    return sanitizeStored(JSON.parse(localStorage.getItem(KEY)), EVENTS);
  } catch {
    return [];
  }
}

export function saveRegistrations(registrations) {
  try {
    localStorage.setItem(KEY, JSON.stringify(registrations));
  } catch {
    // Storage can be full or blocked (private mode). The app keeps working in memory.
  }
}
