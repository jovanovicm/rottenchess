import React from 'react';

function Header() {
  return (
    <header className="site-header">
      <img src="/icons/rotten_chess_pawn.png" alt="RottenChess logo" className="site-logo" />
      <div className="site-title">
        <h1>RottenChess.com</h1>
        <p>A leaderboard of blunders, mistakes, and inaccuracies!</p>
      </div>
    </header>
  );
}

export default Header;