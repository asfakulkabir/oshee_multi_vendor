document.addEventListener("DOMContentLoaded", function () {
    new Swiper('.desktopSwiper', {
        loop: true,
        autoplay: { delay: 4000 },
        speed: 1000,  // ✅ smooth transition
        effect: 'slide',
        pagination: {
            el: '.desktop-pagination',
            clickable: true
        },
        navigation: {
            nextEl: '.desktop-next',
            prevEl: '.desktop-prev'
        },
    });

    new Swiper('.mobileSwiper', {
        loop: true,
        autoplay: { delay: 4000 },
        speed: 1000,  // ✅ smooth transition
        effect: 'slide',
        pagination: {
            el: '.mobile-pagination',
            clickable: true
        }
    });

 new Swiper(".productSwiper", {
    slidesPerView: 2,
    spaceBetween: 16,
    slidesPerGroup: 2,
    loop: false,
    autoplay: { delay: 4000 },
    speed: 1000,  
    grabCursor: true,
    navigation: {
      nextEl: ".swiper-button-next",
      prevEl: ".swiper-button-prev",
    },
    breakpoints: {
      640: {
        slidesPerView: 2,
        slidesPerGroup: 2,
      },
      768: {
        slidesPerView: 3,
        slidesPerGroup: 3,
      },
      1024: {
        slidesPerView: 4,
        slidesPerGroup: 4,
      },
      1280: {
        slidesPerView: 5,
        slidesPerGroup: 5,
      },
    },
  });

});

document.addEventListener("DOMContentLoaded", function () {
    new Swiper('.testimonialDesktopSwiper', {
        loop: true,
        autoplay: {
            delay: 4000,
            disableOnInteraction: false
        },
        speed: 1000,
        slidesPerView: 1,
        pagination: {
            el: '.swiper-pagination',
            clickable: true
        }
    });

    new Swiper('.testimonialMobileSwiper', {
        loop: true,
        autoplay: {
            delay: 4000,
            disableOnInteraction: false
        },
        speed: 1000,
        slidesPerView: 1,
        pagination: {
            el: '.swiper-pagination',
            clickable: true
        }
    });

    new Swiper(".categorySwiper", {
    slidesPerView: 4,
    spaceBetween: 12,
    navigation: {
      nextEl: ".swiper-button-next",
      prevEl: ".swiper-button-prev",
    },
    breakpoints: {
      640: {
        slidesPerView: 6,
        spaceBetween: 12,
      },
      768: {
        slidesPerView: 8,
        spaceBetween: 16,
      },
      1024: {
        slidesPerView: 10,
        spaceBetween: 20,
      },
    },
  });

});