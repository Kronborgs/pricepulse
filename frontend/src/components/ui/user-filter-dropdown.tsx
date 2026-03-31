"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Search, Users, X } from "lucide-react";
import { User } from "@/types";

interface UserFilterDropdownProps {
  users: User[];
  selected: string[];
  onChange: (ids: string[]) => void;
}

export function UserFilterDropdown({ users, selected, onChange }: UserFilterDropdownProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = users.filter((u) => {
    const name = (u.display_name ?? u.email).toLowerCase();
    return name.includes(search.toLowerCase());
  });

  function toggle(id: string) {
    if (selected.includes(id)) {
      onChange(selected.filter((s) => s !== id));
    } else {
      onChange([...selected, id]);
    }
  }

  function clearAll() {
    onChange([]);
  }

  const label =
    selected.length === 0
      ? "Alle brugere"
      : selected.length === 1
      ? (users.find((u) => u.id === selected[0])?.display_name ??
         users.find((u) => u.id === selected[0])?.email ??
         "1 bruger")
      : `${selected.length} brugere`;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex h-9 items-center gap-1.5 rounded-md border border-input bg-background px-2.5 text-sm hover:bg-muted transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
      >
        <Users className="h-4 w-4 text-muted-foreground shrink-0" />
        <span className={selected.length > 0 ? "font-medium" : "text-muted-foreground"}>
          {label}
        </span>
        {selected.length > 0 && (
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => { e.stopPropagation(); clearAll(); }}
            onKeyDown={(e) => { if (e.key === "Enter") { e.stopPropagation(); clearAll(); } }}
            className="ml-0.5 rounded-full p-0.5 hover:bg-muted-foreground/20 text-muted-foreground cursor-pointer"
            aria-label="Ryd filter"
          >
            <X className="h-3 w-3" />
          </span>
        )}
        <ChevronDown className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-1 w-56 rounded-md border border-border bg-background shadow-md">
          {/* Search */}
          <div className="p-2 border-b border-border">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <input
                autoFocus
                type="search"
                placeholder="Søg bruger…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-md border border-input bg-background pl-7 pr-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>

          {/* "Alle brugere" option */}
          <div className="p-1">
            <button
              type="button"
              onClick={() => { clearAll(); setOpen(false); }}
              className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm transition-colors hover:bg-muted ${
                selected.length === 0 ? "font-semibold text-foreground" : "text-muted-foreground"
              }`}
            >
              Alle brugere
            </button>
          </div>

          <div className="border-t border-border" />

          {/* User list */}
          <div className="max-h-52 overflow-y-auto p-1">
            {filtered.length === 0 ? (
              <p className="px-2 py-2 text-xs text-muted-foreground">Ingen brugere fundet</p>
            ) : (
              filtered.map((u) => {
                const name = u.display_name ?? u.email;
                const checked = selected.includes(u.id);
                return (
                  <label
                    key={u.id}
                    className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(u.id)}
                      className="h-4 w-4 rounded border-input accent-primary"
                    />
                    <span className="truncate">{name}</span>
                  </label>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
