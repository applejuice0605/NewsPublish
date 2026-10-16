(function () {
  'use strict';

  var VOICE_LABELS = { 'zh-CN-YunyangNeural': '云扬 · 中文男声' };

  function reportDate() {
    var pathMatch = window.location.pathname.match(/\/reports\/(\d{4}-\d{2}-\d{2})(?:\/|\.html)/);
    if (pathMatch) return pathMatch[1];
    var generated = Array.from(document.querySelectorAll('.info-item')).find(function (item) {
      var label = item.querySelector('.info-label');
      return label && label.textContent.trim() === '生成时间';
    });
    var value = generated && generated.querySelector('.info-value');
    var dateMatch = value && value.textContent.match(/(\d{2}-\d{2})/);
    return dateMatch ? dateMatch[1] : '';
  }

  function matchesReport(metadata) {
    var current = reportDate();
    if (!current || !metadata.date) return false;
    return current.length === 5 ? metadata.date.slice(5) === current : metadata.date === current;
  }

  function panelMarkup(metadata) {
    var section = document.createElement('section');
    section.className = 'speech-panel';
    section.setAttribute('aria-labelledby', 'podcastTitle');
    var heading = document.createElement('div');
    heading.className = 'speech-panel-head';
    heading.innerHTML = '<h2 class="speech-panel-title" id="podcastTitle">今日 AI 新闻播报</h2>' +
      '<span class="speech-badge">AI 播客</span>';
    var player = document.createElement('div');
    player.className = 'podcast-slot';
    var audio = document.createElement('audio');
    audio.className = 'podcast-audio';
    audio.controls = true;
    audio.preload = 'metadata';
    audio.src = metadata.audio_url;
    audio.setAttribute('aria-label', metadata.date + ' AI 新闻播报');
    var meta = document.createElement('span');
    meta.className = 'podcast-meta';
    meta.textContent = metadata.date + ' · ' +
      (metadata.voice_label || VOICE_LABELS[metadata.voice] || '自然中文语音');
    player.append(audio, meta);
    section.append(heading, player);
    return section;
  }

  function init() {
    var content = document.querySelector('.content');
    if (!content || !window.fetch) return;
    fetch('/audio/latest.json', { cache: 'no-store' })
      .then(function (response) {
        if (!response.ok) throw new Error('unavailable');
        return response.json();
      })
      .then(function (metadata) {
        if (!metadata.audio_url || !matchesReport(metadata)) return;
        content.insertBefore(panelMarkup(metadata), content.firstChild);
      })
      .catch(function () { /* A daily AI podcast is optional. */ });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
