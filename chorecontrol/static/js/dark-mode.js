// Dark mode toggle with system preference detection
(function() {
  const html = document.documentElement;
  const toggle = document.getElementById('theme-toggle');

  // Check for saved preference or system preference
  const savedTheme = localStorage.getItem('chorecontrol-theme');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  // Apply theme on page load
  if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
    html.classList.add('dark');
  } else {
    html.classList.remove('dark');
  }

  // Toggle theme on button click
  if (toggle) {
    toggle.addEventListener('click', () => {
      html.classList.toggle('dark');
      const isDark = html.classList.contains('dark');
      localStorage.setItem('chorecontrol-theme', isDark ? 'dark' : 'light');
    });
  }

  // Listen for system theme changes (only if user hasn't manually set a preference)
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('chorecontrol-theme')) {
      if (e.matches) {
        html.classList.add('dark');
      } else {
        html.classList.remove('dark');
      }
    }
  });
})();
