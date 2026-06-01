export default function Skeleton() {
  return (
    <>
      <div className="skeleton-grid">
        <div className="skel" style={{ height: 80 }} />
        <div className="skel" style={{ height: 80 }} />
        <div className="skel" style={{ height: 80 }} />
        <div className="skel" style={{ height: 80 }} />
      </div>
      <div className="skel" style={{ height: 220, marginBottom: '1.25rem' }} />
      <div className="skel" style={{ height: 80, marginBottom: '1.25rem' }} />
    </>
  )
}
