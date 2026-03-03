document.addEventListener("DOMContentLoaded", () => {
  // Add dark mode toggle support
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
  const toggleBtn = document.createElement('button');
  toggleBtn.className = 'apple-btn apple-btn-secondary';
  toggleBtn.style.padding = '8px 16px';
  toggleBtn.style.fontSize = '0.9rem';
  toggleBtn.style.marginLeft = '1rem';

  const updateTheme = (isDark) => {
    document.body.classList.toggle('apple-theme-dark', isDark);
    toggleBtn.textContent = isDark ? '☀ Light' : '◐ Dark';
    // Update css vars if needed for custom manual override
    if (isDark) {
      document.documentElement.style.setProperty('--apple-bg', '#000000');
      document.documentElement.style.setProperty('--apple-text', '#f5f5f7');
      document.documentElement.style.setProperty('--apple-glass-bg', 'rgba(28, 28, 30, 0.7)');
    } else {
      document.documentElement.style.setProperty('--apple-bg', '#f5f5f7');
      document.documentElement.style.setProperty('--apple-text', '#1d1d1f');
      document.documentElement.style.setProperty('--apple-glass-bg', 'rgba(255, 255, 255, 0.7)');
    }
  };

  // Check initial state
  let isDarkMode = prefersDark.matches;
  updateTheme(isDarkMode);

  toggleBtn.addEventListener('click', () => {
    isDarkMode = !isDarkMode;
    updateTheme(isDarkMode);
  });

  const navLinks = document.querySelector('.apple-nav-links');
  if(navLinks) {
    navLinks.appendChild(toggleBtn);
  }

  // Add subtle mouse tracking effect to showcase
  const showcase = document.querySelector('.apple-showcase-inner');
  if (showcase) {
    document.addEventListener('mousemove', (e) => {
      const xAxis = (window.innerWidth / 2 - e.pageX) / 50;
      const yAxis = (window.innerHeight / 2 - e.pageY) / 50;
      showcase.style.transform = `rotateY(${xAxis}deg) rotateX(${yAxis}deg)`;
    });

    // Reset on mouse leave
    document.addEventListener('mouseleave', () => {
      showcase.style.transform = `rotateY(0deg) rotateX(0deg)`;
      showcase.style.transition = `transform 0.5s ease`;
    });
  }
});
