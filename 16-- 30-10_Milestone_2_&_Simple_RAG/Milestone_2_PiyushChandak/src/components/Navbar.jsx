import { NavLink } from "react-router-dom";

export default function Navbar({ count }) {
  return (
    <header className="masthead">
      <div className="container masthead-inner">
        <span className="brand">Community Learning Centre</span>
        <nav aria-label="Main">
          <NavLink to="/" end>
            Events
          </NavLink>
          <NavLink to="/registrations">
            Registrations <span className="count">{count}</span>
          </NavLink>
        </nav>
      </div>
    </header>
  );
}
