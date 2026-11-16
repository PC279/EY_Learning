import test from "node:test";
import assert from "node:assert/strict";
import { EVENTS } from "../data/events.js";
import {
  addRegistration,
  cancelRegistration,
  sanitizeStored,
  seatsLeft,
  validateRegistration,
} from "./registrations.js";

const cloud = EVENTS[0]; // 4 seats
const art = EVENTS[5]; // 2 seats
const person = (n) => ({ name: `Person ${n}`, email: `p${n}@example.com` });

function fill(event, count) {
  let regs = [];
  for (let i = 0; i < count; i++) {
    const result = addRegistration(regs, event, person(i));
    assert.ok(result.ok);
    regs = result.registrations;
  }
  return regs;
}

test("starting state: seats left equal capacity for every event", () => {
  for (const e of EVENTS) assert.equal(seatsLeft(e, []), e.seats);
});

test("valid registration is stored and uses one seat", () => {
  const r = addRegistration([], cloud, { name: "  Asha Rao ", email: " Asha@Example.com " });
  assert.ok(r.ok);
  assert.equal(r.registrations.length, 1);
  assert.equal(r.registrations[0].name, "Asha Rao");
  assert.equal(r.registrations[0].email, "Asha@Example.com");
  assert.equal(seatsLeft(cloud, r.registrations), 3);
});

test("missing name, missing email and bad email are rejected", () => {
  assert.ok(validateRegistration({ name: "", email: "a@b.co" }).name);
  assert.ok(validateRegistration({ name: "   ", email: "a@b.co" }).name);
  assert.ok(validateRegistration({ name: "A", email: "" }).email);
  for (const bad of ["plain", "a@b", "a@@b.co", "a b@c.co", "@b.co", "a@.co"]) {
    assert.ok(validateRegistration({ name: "A", email: bad }).email, bad);
  }
  assert.deepEqual(validateRegistration({ name: "A", email: "a@b.co" }), {});
  const r = addRegistration([], cloud, { name: "", email: "" });
  assert.equal(r.ok, false);
  assert.equal(seatsLeft(cloud, []), 4);
});

test("over long input is rejected", () => {
  assert.ok(validateRegistration({ name: "x".repeat(81), email: "a@b.co" }).name);
  assert.ok(validateRegistration({ name: "A", email: `${"x".repeat(250)}@b.co` }).email);
});

test("same email twice for one event is blocked, ignoring case and spaces", () => {
  const first = addRegistration([], cloud, { name: "A", email: "sam@example.com" });
  const again = addRegistration(first.registrations, cloud, { name: "B", email: "  SAM@Example.COM " });
  assert.equal(again.ok, false);
  assert.ok(again.errors.email);
});

test("same email can register for a different event", () => {
  const first = addRegistration([], cloud, { name: "A", email: "sam@example.com" });
  const other = addRegistration(first.registrations, art, { name: "A", email: "sam@example.com" });
  assert.ok(other.ok);
  assert.equal(other.registrations.length, 2);
});

test("a full event rejects further registrations", () => {
  const regs = fill(art, 2);
  assert.equal(seatsLeft(art, regs), 0);
  const r = addRegistration(regs, art, person(99));
  assert.equal(r.ok, false);
  assert.ok(r.errors.form);
});

test("cancelling frees exactly one seat and the person can register again", () => {
  const regs = fill(art, 2);
  const after = cancelRegistration(regs, regs[0].id);
  assert.equal(after.length, 1);
  assert.equal(seatsLeft(art, after), 1);
  assert.ok(addRegistration(after, art, person(0)).ok);
});

test("cancelling an unknown id changes nothing", () => {
  const regs = fill(art, 1);
  assert.equal(cancelRegistration(regs, "nope").length, 1);
});

test("functions do not mutate their input", () => {
  const regs = Object.freeze([...fill(cloud, 1)]);
  const added = addRegistration(regs, cloud, person(50));
  assert.ok(added.ok);
  assert.equal(regs.length, 1);
  cancelRegistration(regs, regs[0].id);
  assert.equal(regs.length, 1);
});

test("sanitizeStored survives junk and tampered data", () => {
  assert.deepEqual(sanitizeStored(null, EVENTS), []);
  assert.deepEqual(sanitizeStored("text", EVENTS), []);
  assert.deepEqual(sanitizeStored({ a: 1 }, EVENTS), []);

  const good = { id: "1", eventId: "EV106", name: "Ok", email: "ok@example.com" };
  const stored = [
    good,
    { ...good }, // duplicate id
    { ...good, id: "2", email: "OK@example.com " }, // duplicate email for the event
    { id: "3", eventId: "EV999", name: "Ghost", email: "g@example.com" }, // unknown event
    { id: "4", eventId: "EV106", name: "", email: "g@example.com" }, // empty name
    { id: "5", eventId: "EV106", name: "X", email: "not an email" },
    { id: 6, eventId: "EV106", name: "X", email: "x@example.com" }, // wrong type
    null,
    "str",
    { ...good, id: "7", email: "b@example.com", extra: "<script>" },
    { ...good, id: "8", email: "c@example.com" }, // beyond capacity of 2
  ];
  const clean = sanitizeStored(stored, EVENTS);
  assert.equal(clean.length, 2);
  assert.deepEqual(Object.keys(clean[1]).sort(), ["email", "eventId", "id", "name"]);
  assert.equal(seatsLeft(art, clean), 0);
});
