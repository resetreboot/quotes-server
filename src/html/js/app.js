/*
 *
 *  This file is part of Quotes Server.
 *
 *  Quotes Server is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  Quotes Server is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with Quotes Server.  If not, see <http://www.gnu.org/licenses/>.
 */

var token = null;
var user = null;

function drawRating(quote_id, rating) {
    var empty_stars = 5 - rating;
    var full_stars = rating;

    $('div#rating-' + quote_id).html('');

    for (var i = 0; i < empty_stars; i++) {
        $('div#rating-' + quote_id).append('<span>☆</span>');
    }

    for (var i = 0; i < full_stars; i++) {
        $('div#rating-' + quote_id).append('<span style="color: gold;">★</span>');
    }

}

function activeMenu(menu) {
    $('a#indexmenu').removeClass('active');
    $('a#bestmenu').removeClass('active');
    $('a#latestmenu').removeClass('active');
    $('a#userlistmenu').removeClass('active');

    $('a#' + menu + 'menu').addClass('active');
}

function addQuote(quote) {
    var html = '<div class="row quote_element"><div class="eleven column quote"><p>';
    html = html + quote.text + '</p>';
    html = html + '<p class="date">Said <span class="momentdate">' + moment(quote.date, 'X').fromNow() + '</span> by:</p>'; 
    html = html + '<h4>' + quote.author + '</h4>'; 
    html = html + '<div class="u-cf"></div>'; 
    html = html + '<p class="rating">Votes: <span id="votes-' + quote.id + '">' + quote.votes + '</span> Rated:&nbsp;';
    html = html + '<div class="rating" id="rating-' + quote.id + '"></div>';
    html = html + '<div class="rater" id="rater-' + quote.id + '" data-quote=' +  quote.id + '>';
    html = html + '<span data-stars="5">☆</span><span data-stars="4">☆</span><span data-stars="3">☆</span><span data-stars="2">☆</span><span data-stars="1">☆</span></div>';
    html = html + '<div style="float:right;" id="ratermessage-' + quote.id + '">Rate!:&nbsp;&nbsp;&nbsp;</div>';
    html = html + '</div></div>';
    $('div#newquoteform').after(html);

    drawRating(quote.id, quote.rating);

    $('div#rater-' + quote.id + ' > span').click(function(event) {
        event.preventDefault();
        var quote_id = $(this).parent().data('quote');
        var stars = parseInt($(this).data('stars'));

        $.ajax({
            type: 'POST',
            contentType: 'application/json',
            headers: {Authorization: token},
            url: SERVER + '/vote/' + quote_id,
            data: JSON.stringify({vote: stars}),
            success: function (data) {
                      $('div#rater-' + quote_id).fadeOut();               
                      $('div#ratermessage-' + quote_id).fadeOut();               
                      drawRating(data.quote.id, data.quote.rating);
                      $('span#votes-' + data.quote.id).html(data.quote.votes);
                    },
            statusCode: {
                401: function() {showLoginForm();}
            }
        });
    });
}

function fetchQuotes() {
    activeMenu('index');
    
    $.ajax({
        url: SERVER,
        type: 'GET',
        headers: {Authorization: token},
        success: function(data) {
                $('div.quote_element').remove();
                for (var i=0; i < data.quotes.length; i++) {
                    addQuote(data.quotes[i]);
                }
            },
        statusCode: {
            401: function() {showLoginForm();}
        }
    });
}

function bestQuotes() {
    activeMenu('best');

    $.ajax({
        url: SERVER + '/best',
        type: 'GET',
        headers: {Authorization: token},
        success: function(data) {
                $('div.quote_element').remove();
                for (var i=data.quotes.length - 1; i > -1; i--) {
                    addQuote(data.quotes[i]);
                }
            },
        statusCode: {
            401: function() {showLoginForm();}
        }
    });
}

function latestQuotes() {
    activeMenu('latest');

    $.ajax({
        url: SERVER + '/latest',
        type: 'GET',
        headers: {Authorization: token},
        success: function(data) {
                $('div.quote_element').remove();
                for (var i=0; i < data.quotes.length; i++) {
                    addQuote(data.quotes[i]);
                }
            },
        statusCode: {
            401: function() {showLoginForm();}
        }
    });
}

function newQuote() {
    var author = $('input#author').val();
    var quote = $('textarea#quotetext').val();

    $('input#author').val('');
    $('textarea#quotetext').val('');

	$.ajax({ 
		type:'POST',
		contentType: 'application/json',
        headers: {Authorization: token},
		url: SERVER + '/quote',
		data: JSON.stringify({author: author, text: quote}),
		success: function (data) {
                   addQuote(data.quote);
                 },
        statusCode: {
            401: function() {showLoginForm();}
        }
	});
}

// User management functions
//
function showLoginForm() {
    eraseCookie('token');
    $('#appcontainer').fadeOut(400, function(){
        $('#loginformcontainer').fadeIn();
    });
}

function loginForm() {
    var username = $('input#username').val();
    var password = $('input#password').val();

    $.ajax({
        type: 'POST',
        contentType: 'application/json',
        url: SERVER + '/login',
        data: JSON.stringify({username: username, password: password}),
        success: function(data) {
            token = data.token;
            user = data.user;
            createCookie('token', data.token, 7);
            $('#loginformcontainer').fadeOut(400, function() {
                $('#appcontainer').fadeIn(400, latestQuotes);
            });
            adminControls();
        }
    });
}

function changePassword() {
    var current = $('input#currentpassword').val();
    var newPass = $('input#passwordnew').val();

    if (newPass === '') {
        alert("Password can't be empty.");
        return;
    }

    $.ajax({
        type: 'POST',
        url: SERVER + '/change_password',
        contentType: 'application/json',
        headers: {Authorization: token},
        data: JSON.stringify({old_pass: current,
               new_pass: newPass}),
        success: function(data) {
                if (data.result) {
                    alert('Password successfully changed');
                } else {
                    alert('Password not changed');
                }
                $('div#changePassModal').hide();
            },
        statusCode: {
            401: function() {showLoginForm();},
            400: function() {
                    alert("Error"); 
                    $('div#changePassModal').hide();
            },
        }
    });

}

function addUserList(user) {
    var html = '<div class="row user_element"><hr />';
    html = html + '<h5>' + user.name + '</h5>';
    html = html + '<div class="one columns">';
    html = html + '<div class="row">Email: </div>';
    html = html + '<div class="row">Active: </div>';
    html = html + '<div class="row">Admin: </div>';
    html = html + '</div>';
    html = html + '<div class="seven columns">';
    html = html + '<div class="row">' + user.email + '</div>';
    if (user.active) {
        html = html + '<div class="row" style="color: #0c0;">✓</div>';
    } else {
        html = html + '<div class="row" style="color: #c00;">❌</div>';
    }
    if (user.admin) {
        html = html + '<div class="row" style="color: #0c0;">✓</div>';
    } else {
        html = html + '<div class="row" style="color: #c00;">❌</div>';
    }
    html = html + '</div>';
    html = html + '</div>';
    $('h3#userheader').after(html);
}

function fetchUsers() {
    if (!user.admin) {
        return;
    }

    activeMenu('userlist');

    $.ajax({
        url: SERVER + '/users',
        type: 'GET',
        headers: {Authorization: token},
        success: function(data) {
                $('div.user_element').remove();
                for (var i=0; i < data.users.length; i++) {
                    addUserList(data.users[i]);
                }
                $('div#userlistModal').show();
            },
        statusCode: {
            401: function() {showLoginForm();}
        }
    });
}
function newUser() {
    if (!user.admin) {
        $('div#registerModal').hide();
        return;
    }

    var username = $('input#newuser').val();
    var email = $('input#newemail').val();
    var password = $('input#newpassword').val();

    $.ajax({
        type: 'POST',
        url: SERVER + '/register',
        contentType: 'application/json',
        headers: {Authorization: token},
        data: JSON.stringify({username: username,
               email: email,
               password: password}),
        success: function() {
                alert('User successfully registered');
                $('div#registerModal').hide();
            },
        statusCode: {
            401: function() {showLoginForm();},
            400: function() {
                    alert("Error"); 
                    $('div#registerModal').hide();
            },
            403: function() {
                    alert("Admin only function"); 
                    $('div#registerModal').hide();
            }
        }
    });
}

function adminControls() {
    if (user.admin) {
        $('.adminonly').show();
    } else {
        $('.adminonly').hide();
    }
}

function loadUserData() {
	$.ajax({ 
		type:'GET',
		contentType: 'application/json',
        headers: {Authorization: token},
		url: SERVER + '/me',
		success: function (data) {
                   user = data.user;
                   adminControls();
                 }
	});
}

function logOut() {
    $.ajax({
        type: 'POST',
        url: SERVER + '/logout',
        success: function() {
            token = null;
            user = null;
            eraseCookie('token');
            showLoginForm();
        }
    });
}

// Cookie handling functions
//
function createCookie(name,value,days) {
    if (days) {
            var date = new Date();
            date.setTime(date.getTime()+(days*24*60*60*1000));
            var expires = "; expires="+date.toGMTString();
        }
    else var expires = "";
    document.cookie = name+"="+value+expires+"; path=/";
}

function readCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
            var c = ca[i];
            while (c.charAt(0)==' ') c = c.substring(1,c.length);
            if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
        }
    return null;
}

function eraseCookie(name) {
    createCookie(name,"",-1);
}
