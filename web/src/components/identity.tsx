export function BrandMark({ className = "" }: { className?: string }) {
  return <svg className={className} width="36" height="36" viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <circle cx="20" cy="20" r="15" stroke="currentColor" strokeWidth="1.5" />
    <ellipse cx="20" cy="20" rx="6.5" ry="15" transform="rotate(30 20 20)" stroke="currentColor" strokeWidth="1.5" />
    <path d="M4 24 36 16" stroke="currentColor" strokeWidth="1.5" />
  </svg>;
}

export function Globe() {
  return <div className="globe-composition" aria-hidden="true">
    <div className="globe-coordinate coordinate-top">CROSS-CONTEXT MODEL EVALUATION</div>
    <svg className="globe-svg" viewBox="0 0 600 600" fill="none">
      <defs>
        <radialGradient id="sphere-fill" cx="40%" cy="32%" r="75%"><stop stopColor="#e6e9d6"/><stop offset="1" stopColor="#becfbc"/></radialGradient>
        <clipPath id="sphere-clip"><circle cx="300" cy="300" r="201"/></clipPath>
        <linearGradient id="orbit-fade"><stop stopColor="#47755d" stopOpacity=".1"/><stop offset=".5" stopColor="#47755d"/><stop offset="1" stopColor="#47755d" stopOpacity=".1"/></linearGradient>
      </defs>
      <circle cx="300" cy="300" r="269" stroke="#cbd0c3" strokeDasharray="2 8"/>
      <path d="M300 10V62M300 538V590M10 300H62M538 300H590" stroke="#b6c2b2"/>
      <circle cx="300" cy="300" r="201" fill="url(#sphere-fill)" stroke="#819d81" strokeWidth=".8"/>
      <g clipPath="url(#sphere-clip)" transform="rotate(-24 300 300)" stroke="#709373" strokeWidth=".75" opacity=".72">
        {[32, 66, 105, 148, 182, 201].map(r => <ellipse key={r} cx="300" cy="300" rx={r} ry="201"/>)}
        {[118, 151, 197, 248, 300, 352, 403, 449, 482].map((y, i) => <ellipse key={y} cx="300" cy={y} rx={Math.sqrt(201 ** 2 - (y - 300) ** 2)} ry={11 + (4 - Math.abs(i - 4)) * 8}/>)}
        <path d="m221 306 17-18 29 3 15 15 29 5 18 20-9 31-16 10-3 24-16 26-12 29-12-6 2-33-9-29-13-15-2-31-15-13Z" fill="#759873" fillOpacity=".58" stroke="#517d57" strokeWidth="1.5"/>
        <path d="m209 168 33-24 45 7 10 22-16 23 10 17-14 25-22-4-18 24-12-8 2-28-24-15-6-24Z M327 169l35-16 34 15 13 34-23 17-32-7-19 15-15-22Z m16 65 29-7 30 25 11 33-18 36-21 39-20-6-9-46-20-24Z" strokeOpacity=".45" fill="#809d77" fillOpacity=".2"/>
      </g>
      <ellipse className="globe-orbit" cx="300" cy="300" rx="285" ry="74" transform="rotate(-24 300 300)" stroke="url(#orbit-fade)" strokeWidth="1.2"/>
      <path d="M268 380 183 451H60" stroke="#436e52" strokeWidth="1"/>
      <circle className="globe-beacon" cx="268" cy="380" r="15" fill="#dce9b6" fillOpacity=".4"/>
      <circle cx="268" cy="380" r="5" fill="#244c35" stroke="#e2edc6" strokeWidth="2"/>
      <circle cx="416" cy="202" r="3" fill="#5a7754"/>
      <path d="M416 202 468 150H541" stroke="#769077" strokeWidth=".8"/>
      <text x="61" y="477" fill="#294a37" fontSize="12" fontFamily="monospace" letterSpacing="2">BRAZIL · PT-BR</text>
      <text x="471" y="137" fill="#627561" fontSize="10" fontFamily="monospace" letterSpacing="1">EU BASELINE</text>
    </svg>
    <div className="globe-note"><span className="status-dot"/>BRAZIL · PL 2338/2023</div>
    <span className="globe-coordinate coordinate-bottom">RESEARCH IN PROGRESS / 2026</span>
  </div>;
}
