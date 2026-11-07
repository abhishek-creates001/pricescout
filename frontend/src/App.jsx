import { useEffect, useMemo, useState } from "react";

const money = (n) => "₹" + Math.round(n).toLocaleString("en-IN");

export default function App() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sortBy, setSortBy] = useState("effective");
  const [hideOos, setHideOos] = useState(false);

  useEffect(() => {
    fetch("/api/suggestions")
      .then((r) => r.json())
      .then(setSuggestions)
      .catch(() => setError("Can’t reach the backend. Is it running on port 5000?"));
  }, []);

  async function search(q = query) {
    q = q.trim();
    if (!q) return;
    setQuery(q);
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/compare?q=${encodeURIComponent(q)}`);
      setData(await res.json());
    } catch {
      setError("Request failed. Check that the backend is running.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  const rows = useMemo(() => {
    if (!data?.offers) return [];
    let list = data.offers.filter((o) => !(hideOos && !o.in_stock));
    const inStock = list.filter((o) => o.in_stock);
    const out = list.filter((o) => !o.in_stock);
    const key = {
      effective: (a, b) => a.effective - b.effective,
      rating: (a, b) => (b.rating ?? 0) - (a.rating ?? 0),
      store: (a, b) => a.store.localeCompare(b.store),
    }[sortBy];
    return [...inStock.sort(key), ...out];
  }, [data, sortBy, hideOos]);

  const best = data?.best;

  return (
    <main className="wrap">
      <header>
        <h1>PriceScout</h1>
        <p className="mute">Compare a product across stores and spot the lowest price.</p>
      </header>

      <form className="bar" onSubmit={(e) => { e.preventDefault(); search(); }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. Sony WH-1000XM5"
          aria-label="Product name"
        />
        <button type="submit" disabled={loading}>{loading ? "Searching…" : "Compare"}</button>
      </form>

      <div className="chips">
        {suggestions.map((s) => (
          <button key={s} className="ghost" onClick={() => search(s)}>{s}</button>
        ))}
      </div>

      {error && <div className="card err">{error}</div>}

      {data && !data.found && <div className="card">No results found for “{query}”.</div>}

      {best && (
        <section className="card rec">
          <div className="mute">Recommended</div>
          <h2>{best.store}</h2>
          <div className="big">{money(best.effective)}</div>
          <p className="mute">
            {data.product} · listed {money(best.price)}
            {best.shipping ? ` + ${money(best.shipping)} shipping` : " · free delivery"}
            {best.discount ? ` − ${money(best.discount)} offer` : ""} · {best.delivery}
          </p>
          {data.savings > 0 && <p><strong>You save {money(data.savings)}</strong> vs the priciest in-stock option.</p>}
          {data.close_call && <p className="mute">Runner-up is within 1%. Consider delivery speed or rating.</p>}
          {best.url && <a className="go" href={best.url} target="_blank" rel="noreferrer">Open store →</a>}
        </section>
      )}

      {data?.found && (
        <section className="card">
          <div className="tools">
            <label>
              Sort by{" "}
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="effective">Lowest price</option>
                <option value="rating">Highest rating</option>
                <option value="store">Store name</option>
              </select>
            </label>
            <label>
              <input type="checkbox" checked={hideOos} onChange={(e) => setHideOos(e.target.checked)} /> Hide out of stock
            </label>
          </div>
          <div className="scroll">
            <table>
              <thead>
                <tr><th>Store</th><th>Price</th><th>Shipping</th><th>Offers</th><th>Effective</th><th>Rating</th><th>Delivery</th></tr>
              </thead>
              <tbody>
                {rows.map((o) => {
                  const isBest = best && o.store === best.store && o.in_stock;
                  return o.in_stock ? (
                    <tr key={o.store} className={isBest ? "best" : ""}>
                      <td>{o.store}{isBest && <span className="tag">Lowest</span>}</td>
                      <td>{money(o.price)}</td>
                      <td>{o.shipping ? money(o.shipping) : "Free"}</td>
                      <td>{o.discount ? "−" + money(o.discount) : "—"}</td>
                      <td><strong>{money(o.effective)}</strong></td>
                      <td>{o.rating ? "★ " + o.rating : "—"}</td>
                      <td>{o.delivery}</td>
                    </tr>
                  ) : (
                    <tr key={o.store}>
                      <td>{o.store}</td>
                      <td>{money(o.price)}</td>
                      <td colSpan="4" className="oos">Out of stock</td>
                      <td>—</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {data.errors?.length > 0 && <p className="mute">Some stores failed: {data.errors.join("; ")}</p>}
        </section>
      )}

      <p className="mute note">
        Effective price = price + shipping − offers. Demo data is built in; connect real store APIs in <code>backend/app.py</code>.
      </p>
    </main>
  );
}
