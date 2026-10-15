(function () {
  'use strict';

  var synth = window.speechSynthesis;
  var state = {
    queue: [],
    index: -1,
    playing: false,
    paused: false,
    token: 0,
    activeElement: null,
    voice: null
  };

  function uniqueElements(elements) {
    return Array.from(new Set(elements.filter(Boolean)));
  }

  function cleanText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  function itemText(link) {
    var item = link.closest('.news-item, .new-item, .rss-item');
    var source = item && item.querySelector('.source-name, .rss-author, .new-source-title');
    var prefix = source ? cleanText(source.textContent) + '。' : '';
    return prefix + cleanText(link.textContent);
  }

  function visible(element) {
    if (!element) return false;
    var style = window.getComputedStyle(element);
    return style.display !== 'none' && style.visibility !== 'hidden';
  }

  function linksForScope(scope) {
    if (scope === 'new') {
      return uniqueElements(Array.from(document.querySelectorAll('.new-section .news-link, .new-section .rss-link')));
    }
    if (scope === 'ai') {
      return uniqueElements(Array.from(document.querySelectorAll('.ai-section .ai-block-content, .ai-section .ai-summary')));
    }
    if (scope === 'current') {
      var activeTab = document.querySelector('.tab-btn.active[data-tab-index]');
      var activeIndex = activeTab && activeTab.dataset.tabIndex;
      var groups = activeIndex && activeIndex !== 'all'
        ? Array.from(document.querySelectorAll('.word-group[data-tab-index="' + activeIndex + '"]'))
        : Array.from(document.querySelectorAll('.word-group[data-tab-index]')).filter(visible);
      if (groups.length) {
        return uniqueElements(groups.flatMap(function (group) {
          return Array.from(group.querySelectorAll('.news-link'));
        }));
      }
    }
    return uniqueElements(Array.from(document.querySelectorAll(
      '.hotlist-section .news-link, .rss-section .rss-link, .standalone-section .news-link'
    )));
  }

  function buildQueue(scope) {
    var elements = linksForScope(scope);
    if (scope === 'ai') {
      return elements.map(function (element) {
        return { element: element, text: cleanText(element.textContent) };
      }).filter(function (entry) { return entry.text; });
    }
    return elements.map(function (element) {
      return { element: element.closest('.news-item, .new-item, .rss-item') || element, text: itemText(element) };
    }).filter(function (entry) { return entry.text; });
  }

  function status(message) {
    var node = document.getElementById('speechStatus');
    if (node) node.textContent = message;
  }

  function setButtons() {
    var pause = document.getElementById('speechPause');
    var stop = document.getElementById('speechStop');
    var previous = document.getElementById('speechPrevious');
    var next = document.getElementById('speechNext');
    if (pause) {
      pause.disabled = !state.playing;
      pause.textContent = state.paused ? '继续' : '暂停';
      pause.setAttribute('aria-pressed', state.paused ? 'true' : 'false');
    }
    if (stop) stop.disabled = !state.playing;
    if (previous) previous.disabled = !state.playing || state.index <= 0;
    if (next) next.disabled = !state.playing || state.index >= state.queue.length - 1;
  }

  function clearHighlight() {
    if (state.activeElement) state.activeElement.classList.remove('speech-active');
    state.activeElement = null;
  }

  function stopReading(message) {
    state.token += 1;
    synth.cancel();
    clearHighlight();
    state.playing = false;
    state.paused = false;
    state.index = -1;
    if (message) status(message);
    setButtons();
  }

  function preferredVoice() {
    var voices = synth.getVoices();
    return voices.find(function (voice) { return /^zh[-_]/i.test(voice.lang); }) ||
      voices.find(function (voice) { return /Chinese|中文|普通话/i.test(voice.name); }) ||
      voices[0] || null;
  }

  function speakIndex(index) {
    if (!state.queue.length || index < 0 || index >= state.queue.length) {
      stopReading('朗读完成');
      return;
    }

    synth.cancel();
    clearHighlight();
    state.index = index;
    state.playing = true;
    state.paused = false;
    var entry = state.queue[index];
    state.activeElement = entry.element;
    if (state.activeElement) {
      state.activeElement.classList.add('speech-active');
      state.activeElement.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }

    var utterance = new SpeechSynthesisUtterance(entry.text);
    var rate = document.getElementById('speechRate');
    utterance.lang = 'zh-CN';
    utterance.rate = rate ? Number(rate.value) : 1;
    utterance.voice = state.voice || preferredVoice();
    var token = ++state.token;
    utterance.onend = function () {
      if (token !== state.token || state.paused) return;
      speakIndex(index + 1);
    };
    utterance.onerror = function (event) {
      if (token !== state.token || event.error === 'canceled' || event.error === 'interrupted') return;
      stopReading('朗读失败：' + event.error);
    };
    status('正在朗读 ' + (index + 1) + ' / ' + state.queue.length + '：' + entry.text.slice(0, 42));
    setButtons();
    synth.speak(utterance);
  }

  function startReading() {
    var scope = document.getElementById('speechScope');
    state.queue = buildQueue(scope ? scope.value : 'new');
    if (!state.queue.length) {
      stopReading('当前范围没有可朗读内容');
      return;
    }
    state.voice = preferredVoice();
    speakIndex(0);
  }

  function togglePause() {
    if (!state.playing) return;
    if (state.paused) {
      synth.resume();
      state.paused = false;
      status('继续朗读 ' + (state.index + 1) + ' / ' + state.queue.length);
    } else {
      synth.pause();
      state.paused = true;
      status('已暂停在 ' + (state.index + 1) + ' / ' + state.queue.length);
    }
    setButtons();
  }

  function panelMarkup() {
    return '<section class="speech-panel" aria-labelledby="speechPanelTitle">' +
      '<div class="speech-panel-head"><h2 class="speech-panel-title" id="speechPanelTitle">网页口播</h2>' +
      '<span class="speech-badge">浏览器本地语音</span></div>' +
      '<div class="speech-controls">' +
      '<label class="sr-only" for="speechScope">朗读范围</label>' +
      '<select class="speech-select" id="speechScope">' +
      '<option value="new">本次新增</option><option value="ai">AI 分析</option>' +
      '<option value="current">当前分类</option><option value="all">全部新闻</option></select>' +
      '<button class="speech-button speech-button-primary" id="speechStart" type="button">开始朗读</button>' +
      '<button class="speech-button" id="speechPause" type="button" aria-pressed="false" disabled>暂停</button>' +
      '<button class="speech-button" id="speechStop" type="button" disabled>停止</button></div>' +
      '<div class="speech-secondary-controls">' +
      '<button class="speech-button" id="speechPrevious" type="button" disabled>上一条</button>' +
      '<button class="speech-button" id="speechNext" type="button" disabled>下一条</button>' +
      '<label for="speechRate">语速</label><select class="speech-select" id="speechRate">' +
      '<option value="0.8">0.8×</option><option value="1" selected>1.0×</option>' +
      '<option value="1.2">1.2×</option><option value="1.5">1.5×</option></select></div>' +
      '<p class="speech-status" id="speechStatus" role="status" aria-live="polite">选择范围后开始朗读，不会自动播放</p>' +
      '</section>';
  }

  function init() {
    var content = document.querySelector('.content');
    if (!content) return;
    if (!('speechSynthesis' in window) || !window.SpeechSynthesisUtterance) {
      var unsupported = document.createElement('section');
      unsupported.className = 'speech-panel';
      unsupported.innerHTML = '<h2 class="speech-panel-title">网页口播</h2><p class="speech-status">当前浏览器不支持网页语音朗读</p>';
      content.insertBefore(unsupported, content.firstChild);
      return;
    }

    var holder = document.createElement('div');
    holder.innerHTML = panelMarkup();
    content.insertBefore(holder.firstChild, content.firstChild);
    document.getElementById('speechStart').addEventListener('click', startReading);
    document.getElementById('speechPause').addEventListener('click', togglePause);
    document.getElementById('speechStop').addEventListener('click', function () { stopReading('已停止朗读'); });
    document.getElementById('speechPrevious').addEventListener('click', function () { speakIndex(Math.max(0, state.index - 1)); });
    document.getElementById('speechNext').addEventListener('click', function () { speakIndex(state.index + 1); });
    document.getElementById('speechScope').addEventListener('change', function () {
      if (state.playing) stopReading('范围已切换，请重新开始朗读');
    });
    synth.onvoiceschanged = function () { state.voice = preferredVoice(); };
    state.voice = preferredVoice();
    setButtons();
  }

  window.addEventListener('pagehide', function () { synth.cancel(); });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden && state.playing && !state.paused) togglePause();
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
