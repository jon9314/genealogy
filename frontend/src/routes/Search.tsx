import { useState } from "react";
import { searchPersons, filterPersons, PersonFilters } from "../lib/api";
import type { Person } from "../lib/types";

export default function SearchPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Person[]>([]);
  const [loading, setLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state
  const [filters, setFilters] = useState<PersonFilters>({});

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const results = await searchPersons(searchQuery);
      setSearchResults(results);
    } catch (error) {
      console.error("Search failed:", error);
      alert("Search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = async () => {
    setLoading(true);
    try {
      const results = await filterPersons(filters);
      setSearchResults(results);
    } catch (error) {
      console.error("Filter failed:", error);
      alert("Filter failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleClearFilters = () => {
    setFilters({});
    setSearchResults([]);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      {/* Search Section */}
      <div className="card">
        <h2>Global Search</h2>
        <p style={{ fontSize: "0.9em", color: "#666", marginBottom: "1rem" }}>
          Search across all people by name, birth, death, title, or notes
        </p>
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
          <input
            type="text"
            placeholder="Search for people..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            style={{ flex: 1, padding: "0.5rem", fontSize: "1rem" }}
          />
          <button className="btn" onClick={handleSearch} disabled={loading || !searchQuery.trim()}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
        <button
          className="btn secondary"
          onClick={() => setShowFilters(!showFilters)}
          style={{ fontSize: "0.9rem" }}
        >
          {showFilters ? "Hide Filters" : "Show Advanced Filters"}
        </button>
      </div>

      {/* Advanced Filters Section */}
      {showFilters && (
        <div className="card">
          <h3>Advanced Filters</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "1rem" }}>
            {/* Missing Data Filters */}
            <div>
              <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "bold" }}>
                Missing Data
              </label>
              <label style={{ display: "block", marginBottom: "0.25rem" }}>
                <input
                  type="checkbox"
                  checked={filters.missing_birth || false}
                  onChange={(e) => setFilters({ ...filters, missing_birth: e.target.checked || undefined })}
                />
                {" "}Missing birth date
              </label>
              <label style={{ display: "block", marginBottom: "0.25rem" }}>
                <input
                  type="checkbox"
                  checked={filters.missing_death || false}
                  onChange={(e) => setFilters({ ...filters, missing_death: e.target.checked || undefined })}
                />
                {" "}Missing death date
              </label>
              <label style={{ display: "block" }}>
                <input
                  type="checkbox"
                  checked={filters.has_approx || false}
                  onChange={(e) => setFilters({ ...filters, has_approx: e.target.checked || undefined })}
                />
                {" "}Has approximate data
              </label>
            </div>

            {/* Surname Filter */}
            <div>
              <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "bold" }}>
                Surname
              </label>
              <input
                type="text"
                placeholder="Filter by surname"
                value={filters.surname || ""}
                onChange={(e) => setFilters({ ...filters, surname: e.target.value || undefined })}
                style={{ width: "100%", padding: "0.5rem" }}
              />
            </div>

            {/* Generation Range */}
            <div>
              <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "bold" }}>
                Generation Range
              </label>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type="number"
                  placeholder="Min"
                  value={filters.min_gen || ""}
                  onChange={(e) => setFilters({ ...filters, min_gen: e.target.value ? parseInt(e.target.value) : undefined })}
                  style={{ width: "80px", padding: "0.5rem" }}
                />
                <span>to</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={filters.max_gen || ""}
                  onChange={(e) => setFilters({ ...filters, max_gen: e.target.value ? parseInt(e.target.value) : undefined })}
                  style={{ width: "80px", padding: "0.5rem" }}
                />
              </div>
            </div>

            {/* Birth Year Range */}
            <div>
              <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "bold" }}>
                Birth Year Range
              </label>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type="number"
                  placeholder="Min"
                  value={filters.birth_year_min || ""}
                  onChange={(e) => setFilters({ ...filters, birth_year_min: e.target.value ? parseInt(e.target.value) : undefined })}
                  style={{ width: "100px", padding: "0.5rem" }}
                />
                <span>to</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={filters.birth_year_max || ""}
                  onChange={(e) => setFilters({ ...filters, birth_year_max: e.target.value ? parseInt(e.target.value) : undefined })}
                  style={{ width: "100px", padding: "0.5rem" }}
                />
              </div>
            </div>

            {/* Sex Filter */}
            <div>
              <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "bold" }}>
                Sex
              </label>
              <select
                value={filters.sex || ""}
                onChange={(e) => setFilters({ ...filters, sex: (e.target.value as "M" | "F") || undefined })}
                style={{ width: "100%", padding: "0.5rem" }}
              >
                <option value="">All</option>
                <option value="M">Male</option>
                <option value="F">Female</option>
              </select>
            </div>
          </div>

          <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
            <button className="btn" onClick={handleFilter} disabled={loading}>
              {loading ? "Filtering..." : "Apply Filters"}
            </button>
            <button className="btn secondary" onClick={handleClearFilters}>
              Clear Filters
            </button>
          </div>
        </div>
      )}

      {/* Results Section */}
      {searchResults.length > 0 && (
        <div className="card">
          <h3>Results ({searchResults.length})</h3>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #ccc" }}>
                  <th style={{ padding: "0.5rem", textAlign: "left" }}>Name</th>
                  <th style={{ padding: "0.5rem", textAlign: "left" }}>Given</th>
                  <th style={{ padding: "0.5rem", textAlign: "left" }}>Surname</th>
                  <th style={{ padding: "0.5rem", textAlign: "left" }}>Birth</th>
                  <th style={{ padding: "0.5rem", textAlign: "left" }}>Death</th>
                  <th style={{ padding: "0.5rem", textAlign: "center" }}>Gen</th>
                  <th style={{ padding: "0.5rem", textAlign: "center" }}>Sex</th>
                </tr>
              </thead>
              <tbody>
                {searchResults.map((person) => (
                  <tr key={person.id} style={{ borderBottom: "1px solid #eee" }}>
                    <td style={{ padding: "0.5rem" }}>{person.name}</td>
                    <td style={{ padding: "0.5rem" }}>{person.given || "—"}</td>
                    <td style={{ padding: "0.5rem" }}>{person.surname || "—"}</td>
                    <td style={{ padding: "0.5rem" }}>{person.birth || "—"}</td>
                    <td style={{ padding: "0.5rem" }}>{person.death || "—"}</td>
                    <td style={{ padding: "0.5rem", textAlign: "center" }}>{person.gen}</td>
                    <td style={{ padding: "0.5rem", textAlign: "center" }}>{person.sex || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {searchResults.length === 0 && (searchQuery || Object.keys(filters).length > 0) && !loading && (
        <div className="card">
          <p style={{ textAlign: "center", color: "#666" }}>No results found</p>
        </div>
      )}
    </div>
  );
}
